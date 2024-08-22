import io
from pathlib import Path
from unittest.mock import MagicMock

import PIL
import pytest
from PIL.Image import Image
from filelock import FileLock

from mezcal.storage import LocalStorage, DirectoryLayout


def test_unknown_directory_layout():
    with pytest.raises(RuntimeError) as e_info:
        _local_storage = LocalStorage(layout='foo')
    assert str(e_info.value) == "'FOO' is not a recognized storage layout"


@pytest.mark.parametrize(
    ('layout', 'expected'),
    [
        (DirectoryLayout.BASIC, '/foo/bar/1'),
        (DirectoryLayout.MD5_ENCODED, '/foo/79693ef14b88881ffa7c1f69787a7f91'),
        (DirectoryLayout.MD5_ENCODED_PAIRTREE, '/foo/79/69/3e/79693ef14b88881ffa7c1f69787a7f91'),
    ]
)
def test_get_dir(layout, expected):
    local_storage = LocalStorage('/foo', layout)
    local_dir = local_storage.get_dir('bar/1')
    assert str(local_dir) == expected


def test_get_file():
    local_storage = LocalStorage('/foo')
    file = local_storage.get_file('bar/1')
    assert str(file.path) == '/foo/bar/1/image.jpg'
    assert str(file) == '/foo/bar/1/image.jpg'


def test_get_file_lock(tmp_path):
    local_storage = LocalStorage(tmp_path)
    file = local_storage.get_file('bar/1')
    assert str(file.lock_path) == str(tmp_path / 'bar/1.lock')
    lock = file.lock
    assert isinstance(lock, FileLock)


def test_image_no_convert(monkeypatch, tmp_path):
    mock_fh = MagicMock(spec=io.FileIO)
    mock_image = MagicMock(spec=Image)
    mock_image.mode = 'RGB'
    monkeypatch.setattr(PIL.Image, 'open', lambda *_: mock_image)

    local_storage = LocalStorage(tmp_path)
    file = local_storage.get_file('bar/1')
    file.create(mock_fh)
    assert mock_image.convert.call_count == 0
    assert mock_image.save.call_count == 1


def test_image_convert(monkeypatch, tmp_path):
    mock_fh = MagicMock(spec=io.FileIO)
    mock_image = MagicMock(spec=Image)
    mock_image.mode = 'RGBA'
    mock_image.convert = MagicMock(return_value=mock_image)
    monkeypatch.setattr(PIL.Image, 'open', lambda *_: mock_image)

    local_storage = LocalStorage(tmp_path)
    file = local_storage.get_file('bar/1')
    file.create(mock_fh)
    assert mock_image.convert.call_count == 1
    assert mock_image.save.call_count == 1


def test_image_failure(monkeypatch, tmp_path):
    mock_fh = MagicMock(spec=io.FileIO)
    mock_image = MagicMock(spec=Image)
    mock_image.save = MagicMock(side_effect=RuntimeError)
    monkeypatch.setattr(PIL.Image, 'open', lambda *_: mock_image)

    local_storage = LocalStorage(tmp_path)
    file = local_storage.get_file('bar/1')
    with pytest.raises(RuntimeError) as e:
        file.create(mock_fh)
        assert str(e) == 'Unable to create mezzanine image'


def test_create_and_delete(tmp_path, datadir):
    local_storage = LocalStorage(tmp_path)
    file = local_storage.get_file('bar/1')
    assert not file.exists
    with open(datadir / 'sample.tif', 'rb') as fh:
        file.create(fh)
    assert file.exists
    file.delete()
    assert not file.exists


def test_delete_non_existent(tmp_path, datadir):
    local_storage = LocalStorage(tmp_path)
    file = local_storage.get_file('bar/1')
    assert not file.exists
    file.delete()
    assert not file.exists


def test_delete_error(monkeypatch, tmp_path, datadir):
    local_storage = LocalStorage(tmp_path)
    file = local_storage.get_file('bar/1')
    mock_rmdir = MagicMock(side_effect=OSError)
    monkeypatch.setattr(Path, 'rmdir', mock_rmdir)
    with pytest.raises(RuntimeError):
        file.delete()
