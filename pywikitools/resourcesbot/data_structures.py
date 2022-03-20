from datetime import datetime
import json
import logging
from typing import Any, Dict, Final, List, Optional, Union

import pywikibot
from urllib.parse import unquote
from pywikitools import fortraininglib
from pywikitools.resourcesbot.changes import ChangeLog, ChangeType

from pywikitools.fortraininglib import TranslationProgress


class FileInfo:
    """
    Holds information on one file that is available on the website
    This shouldn't be modified after creation (is there a way to enforce that?)
    """
    __slots__ = ['file_type', 'url', 'timestamp']
    def __init__(self, file_type: str, url: str, timestamp: Union[datetime, str]):
        self.file_type: str = file_type
        self.url: str = url
        if isinstance(timestamp, datetime):
            self.timestamp: datetime = timestamp
        else:
            try:
                timestamp = timestamp.replace('Z', '+00:00')    # we want to support this format as well
                self.timestamp = datetime.fromisoformat(timestamp)
            except (ValueError, TypeError):
                logger = logging.getLogger('pywikitools.resourcesbot.fileinfo')
                logger.error("Invalid timestamp {timestamp}. {file_type}: {url}.")
                self.timestamp = datetime(1970, 1, 1)

    def __str__(self):
        return f"{self.file_type} {self.url} {self.timestamp.isoformat()}"

class WorksheetInfo:
    """Holds information on one worksheet in one specific language
    Only for worksheets that are at least partially translated
    """
    __slots__ = ['page', 'language_code', 'title', 'progress', '_files']

    def __init__(self, page: str, language_code: str, title: str, progress: TranslationProgress):
        """
        @param page: English name of the worksheet
        @param title: translated worksheet title
        @param progress: how much is already translated"""
        self.page: Final[str] = page
        self.language_code: Final[str] = language_code
        self.title: Final[str] = title
        self.progress: Final[TranslationProgress] = progress
        self._files: Dict[str, FileInfo] = {}

    def add_file_info(self, file_info: Optional[FileInfo] = None,
                      file_type: Optional[str] = None, from_pywikibot: Optional[pywikibot.page.FileInfo] = None):
        """Add information about another file associated with this worksheet.
        You can call the function in two different ways:
        - providing file_info
        - providing file_type and from_pywikibot
        This will log on errors but shouldn't raise exceptions
        """
        if file_info is not None:
            self._files[file_info.file_type] = file_info
            return
        assert file_type is not None and from_pywikibot is not None
        self._files[file_type] = FileInfo(file_type, unquote(from_pywikibot.url), from_pywikibot.timestamp)

    def get_file_infos(self) -> Dict[str, FileInfo]:
        """Returns all available files associated with this worksheet"""
        return self._files

    def has_file_type(self, file_type: str) -> bool:
        """Does the worksheet have a file for download (e.g. "pdf")?"""
        return file_type in self._files

    def get_file_type_info(self, file_type: str) -> Optional[FileInfo]:
        """Returns FileInfo of specified type (e.g. "pdf"), None if not existing"""
        if file_type in self._files:
            return self._files[file_type]
        return None

    def is_incomplete(self) -> bool:
        """A translation is incomplete if most units are translated but at least one is not translated or fuzzy"""
        return self.progress.is_incomplete()


class LanguageInfo:
    """Holds information on all available worksheets in one specific language"""
    __slots__ = 'language_code', 'worksheets'

    def __init__(self, language_code: str):
        self.language_code: Final[str] = language_code
        self.worksheets: Dict[str, WorksheetInfo] = {}

    def add_worksheet_info(self, name: str, worksheet_info: WorksheetInfo):
        self.worksheets[name] = worksheet_info

    def has_worksheet(self, name: str) -> bool:
        return name in self.worksheets

    def get_worksheet(self, name: str) -> Optional[WorksheetInfo]:
        if name in self.worksheets:
            return self.worksheets[name]
        return None

    def worksheet_has_type(self, name: str, file_type: str) -> bool:
        """Convienence method combining LanguageInfo.has_worksheet() and WorksheetInfo.has_file_type()"""
        if name in self.worksheets:
            return self.worksheets[name].has_file_type(file_type)
        return False

    def compare(self, old) -> ChangeLog:
        """
        Compare ourselves to another (older) LanguageInfo object: have there been changes / updates?

        @return data structure with all changes
        """
        change_log = ChangeLog()
        logger = logging.getLogger('pywikitools.resourcesbot.languageinfo')
        if not isinstance(old, LanguageInfo):
            logger.warning("Comparison failed: expected LanguageInfo object.")
            return change_log
        for title, info in self.worksheets.items():
            if title in old.worksheets:
                if info.has_file_type('pdf'):
                    if not old.worksheets[title].has_file_type('pdf'):
                        change_log.add_change(title, ChangeType.NEW_PDF)
                    # TODO resolve TypeError: can't compare offset-naive and offset-aware datetimes
#                    elif old.worksheets[title].get_file_type_info('pdf').timestamp < info.get_file_type_info('pdf').timestamp:
#                        change_log.add_change(title, ChangeType.UPDATED_PDF)
                elif old.worksheets[title].has_file_type('pdf'):
                    change_log.add_change(title, ChangeType.DELETED_PDF)

                if info.has_file_type('odt'):
                    if not old.worksheets[title].has_file_type('odt'):
                        change_log.add_change(title, ChangeType.NEW_ODT)
                    # TODO resolve TypeError: can't compare offset-naive and offset-aware datetimes
#                    elif old.worksheets[title].get_file_type_info('odt').timestamp < info.get_file_type_info('odt').timestamp:
#                        change_log.add_change(title, ChangeType.UPDATED_ODT)
                elif old.worksheets[title].has_file_type('odt'):
                    change_log.add_change(title, ChangeType.DELETED_ODT)
            else:
                change_log.add_change(title, ChangeType.NEW_WORKSHEET)
        for worksheet in old.worksheets:
            if worksheet not in self.worksheets:
                change_log.add_change(worksheet, ChangeType.DELETED_WORKSHEET)

        # TODO Emit also ChangeType.UPDATED_WORKSHEET by saving and comparing version number
        return change_log

    def list_worksheets_with_missing_pdf(self) -> List[str]:
        """ Returns a list of worksheets which are translated but are missing the PDF"""
        return [worksheet for worksheet in self.worksheets if not self.worksheets[worksheet].has_file_type('pdf')]

    def list_incomplete_translations(self) -> List[WorksheetInfo]:
        return [info for _, info in self.worksheets.items() if info.is_incomplete()]

    def count_finished_translations(self) -> int:
        count: int = 0
        for worksheet_info in self.worksheets.values():
            if worksheet_info.has_file_type('pdf'):
                count += 1
        return count


def json_decode(data: Dict[str, Any]):
    """
    Deserializes a JSON-formatted string back into FileInfo / WorksheetInfo / LanguageInfo objects.
    @raises AssertionError if data is malformatted
    """
    if "file_type" in data:
        assert "url" in data and "timestamp" in data
        return FileInfo(data["file_type"], data["url"], data["timestamp"])
    if "translated" in data:
        return fortraininglib.TranslationProgress(**data)
    if "page" in data:
        assert "language_code" in data and "title" in data and "progress" in data
        assert isinstance(data["progress"], TranslationProgress)
        worksheet_info = WorksheetInfo(data["page"], data["language_code"], data["title"], data["progress"])
        if "files" in data:
            for file_info in data["files"]:
                assert isinstance(file_info, FileInfo)
                worksheet_info.add_file_info(file_info=file_info)
        return worksheet_info
    if "worksheets" in data:
        assert "language_code" in data
        language_info = LanguageInfo(data["language_code"])
        for worksheet in data["worksheets"]:
            assert isinstance(worksheet, WorksheetInfo)
            language_info.add_worksheet_info(worksheet.page, worksheet)
        return language_info
    return data


class WorksheetInfoEncoder(json.JSONEncoder):
    """Serializes a LanguageInfo / WorksheetInfo / FileInfo object into a JSON string"""
    def default(self, obj):
        if isinstance(obj, LanguageInfo):
            return {"language_code": obj.language_code, "worksheets": list(obj.worksheets.values())}
        if isinstance(obj, WorksheetInfo):
            worksheet_json: Dict[str, Any] = {
                "page": obj.page,
                "language_code": obj.language_code,
                "title": obj.title,
                "progress": obj.progress
            }
            file_infos: Dict[str, FileInfo] = obj.get_file_infos()
            if file_infos:
                worksheet_json["files"] = list(file_infos.values())
            return worksheet_json
        if isinstance(obj, FileInfo):
            return { "file_type": obj.file_type, "url": obj.url, "timestamp": obj.timestamp.isoformat() }
        if isinstance(obj, TranslationProgress):
            return { "translated": obj.translated, "fuzzy": obj.fuzzy, "total": obj.total }
        return super().default(obj)
