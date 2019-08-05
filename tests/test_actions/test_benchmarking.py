import pytest
import asyncio
from pathlib import Path

from lib.utils import alist, benchmark


class TestASNFileStorage:

    @staticmethod
    async def cleanup_one(tmp_path, asn_encoded_multi):
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000001.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        expected_file.unlink()

    @staticmethod
    async def cleanup_four(tmp_path, asn_encoded_multi):
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000001.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[0]
        expected_file.unlink()
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_840001ff.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[1]
        expected_file.unlink()
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_a5050001.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[2]
        expected_file.unlink()
        expected_file = Path(tmp_path/'Encoded/TCAP_MAP/127.0.0.1_00000000.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_encoded_multi[3]
        expected_file.unlink()

    @staticmethod
    async def cleanup_many(tmp_path, num_files):
        path = Path(tmp_path/'Encoded/TCAP_MAP/')
        assert sum(1 for _ in path.iterdir()) == num_files
        for file in path.iterdir():
            file.unlink()

    @staticmethod
    async def do_one(file_storage_action_binary, asn_objects):
        await file_storage_action_binary.async_do_one(asn_objects[0])

    @staticmethod
    async def do_many(file_storage_action_binary, asn_objects):
        coros = []
        for asn_object in asn_objects:
            coro = file_storage_action_binary.async_do_one(asn_object)
            coros.append(coro)
        await asyncio.wait(coros)

    @pytest.mark.asyncio
    async def test_00_do_one_close(self, tmp_path, file_storage_action_binary, asn_objects, asn_encoded_multi):
        await benchmark(self.do_one, file_storage_action_binary, asn_objects, cleanup=self.cleanup_one,
                        cleanup_args=(tmp_path, asn_encoded_multi), num_items=1)

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, file_storage_action_binary, asn_objects, asn_encoded_multi):
        await benchmark(self.do_many, file_storage_action_binary, asn_objects, cleanup=self.cleanup_four,
                        cleanup_args=(tmp_path, asn_encoded_multi), num_items=4)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(['asn_objects_many', 'number'], [[1024, 1024]], indirect=['asn_objects_many'])
    async def test_01_do_thousand(self, tmp_path, file_storage_action_binary, asn_objects_many, number):
        await benchmark(self.do_many, file_storage_action_binary, asn_objects_many, cleanup=self.cleanup_many,
                        cleanup_args=(tmp_path, number), num_items=number)


class TestManagedFileASN:
    @staticmethod
    async def cleanup(asn_codec, managed_file_binary, timestamp, num_objects):
        path = managed_file_binary.path
        objects = asn_codec.from_file(path, received_timestamp=timestamp)
        assert len(await alist(objects)) == num_objects
        assert managed_file_binary.num_files() == 0
        path.unlink()

    @staticmethod
    async def do_one(managed_file_binary, asn_objects):
        managed_file_binary.write(asn_objects[0])
        await managed_file_binary.close()

    @staticmethod
    async def do_many_four(managed_file_binary, asn_objects):
        for asn_object in asn_objects:
            managed_file_binary.write(asn_object)
        await managed_file_binary.close()

    @pytest.mark.asyncio
    async def test_00_do_one_close(self, managed_file_binary, asn_objects, asn_codec, timestamp):
        await benchmark(self.do_one, managed_file_binary, asn_objects, cleanup=self.cleanup,
                        cleanup_args=(asn_codec, managed_file_binary, timestamp, 1))

    @pytest.mark.asyncio
    async def test_01_do_four_close(self, managed_file_binary, asn_objects, asn_codec, timestamp):
        await benchmark(self.do_many_four, managed_file_binary, asn_objects, cleanup=self.cleanup,
                        cleanup_args=(asn_codec, managed_file_binary, timestamp, 4))


class TestASNBufferedFileStorage:

    @staticmethod
    async def cleanup(tmp_path, asn_codec, num_objects):
        path = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert path.exists()
        objects = asn_codec.from_file(path,)
        assert len(await alist(objects)) == num_objects
        path.unlink()

    @staticmethod
    async def do_one(buffered_file_storage_action_binary, asn_objects):
        await buffered_file_storage_action_binary.do_many([asn_objects[0]])

    @staticmethod
    async def do_many(buffered_file_storage_action_binary, asn_objects):
        buffered_file_storage_action_binary.do_many(asn_objects)
        await asyncio.wait_for(buffered_file_storage_action_binary.close(), 5)

    @pytest.mark.asyncio
    async def test_00_do_one_close(self, tmp_path, buffered_file_storage_action_binary, asn_objects, asn_codec):
        await benchmark(self.do_one, buffered_file_storage_action_binary, asn_objects, cleanup=self.cleanup,
                        cleanup_args=(tmp_path, asn_codec, 1))

    @pytest.mark.asyncio
    async def test_00_do_one_close(self, tmp_path, buffered_file_storage_action_binary, asn_objects, asn_codec):
        await benchmark(self.do_many, buffered_file_storage_action_binary, asn_objects, cleanup=self.cleanup,
                        cleanup_args=(tmp_path, asn_codec, 4))

    @pytest.mark.asyncio
    async def test_00_do_one(self, tmp_path, buffered_file_storage_action_binary, asn_object, asn_one_encoded, asn_codec):
        buffered_file_storage_action_binary.do_many([asn_object])
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_one_encoded
        msg = await asn_codec.one_from_file(expected_file)
        assert msg == asn_object

    @pytest.mark.asyncio
    async def test_01_do_many_close(self, tmp_path, buffered_file_storage_action_binary, asn_objects, asn_buffer, asn_codec):
        buffered_file_storage_action_binary.do_many(asn_objects)
        await buffered_file_storage_action_binary.close()
        expected_file = Path(tmp_path/'Encoded/127.0.0.1_TCAP_MAP.TCAP_MAP')
        assert expected_file.exists()
        assert expected_file.read_bytes() == asn_buffer
        msgs = await alist(asn_codec.from_file(expected_file))
        assert msgs == asn_objects


