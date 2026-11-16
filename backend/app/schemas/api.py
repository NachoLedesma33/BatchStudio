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


class CreateSessionRequest(BaseModel):
    name: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    name: Optional[str] = None
    state: Optional[dict[str, Any]] = None


class PreviewRequest(BaseModel):
    kind: str
    session_id: Optional[str] = None
    params: dict[str, Any] = Field(default_factory=dict)


class CreateJobRequest(PreviewRequest):
    pass


class RevealRequest(BaseModel):
    path: str


class SavePathRequest(BaseModel):
    initial_dir: Optional[str] = None
    initial_name: Optional[str] = None


class PickFolderRequest(BaseModel):
    initial_dir: Optional[str] = None


class PickFilesRequest(BaseModel):
    initial_dir: Optional[str] = None
    multiple: bool = True
