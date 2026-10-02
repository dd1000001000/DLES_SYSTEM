# -*- coding: utf-8 -*-
import os

from fastapi import UploadFile

CHUNK_SIZE = 1024 * 1024


def safe_filename(filename: str | None) -> str:
    """去掉客户端提供的文件名中的目录部分，只保留最后一段"""
    return os.path.basename((filename or '').replace('\\', '/')).strip()


def save_upload(upload: UploadFile, dest_path: str, max_bytes: int) -> None:
    """把上传文件写到 dest_path，超过 max_bytes 则删除已写内容并报错"""
    written = 0
    try:
        with open(dest_path, 'wb') as out:
            while True:
                chunk = upload.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise Exception(f'文件不能超过 {max_bytes // (1024 * 1024)} MB')
                out.write(chunk)
    except Exception:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise
