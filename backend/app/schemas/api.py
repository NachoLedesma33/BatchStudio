from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ImportPathsRequest(BaseModel):
    paths: List[str] = Field(default_factory=list)


class ImportFolderRequest(BaseModel):
    folder: str
    recursive: bool = True


class ReorderRequest(BaseModel):
    ids: List[str]


class UpdateDocumentRequest(BaseModel):
    included: Optional[bool] = None
    name: Optional[str] = None


class MergeJobRequest(BaseModel):
    output_path: Optional[str] = None
    overwrite: bool = False


class SaveSessionRequest(BaseModel):
    name: Optional[str] = None


class LoadSessionRequest(BaseModel):
    path: str
