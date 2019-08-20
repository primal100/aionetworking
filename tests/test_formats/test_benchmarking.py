import pickle
import pytest
from pathlib import Path
from lib.formats.base import BufferObject
from lib.utils import Record


class TestRecording:
    @pytest.mark.asyncio
    async def test_00_pickle(self, asn1_recording_data, tmpdir, pickle_codec, benchmark):
        recording_path = Path(tmpdir / 'recording.pickle')

        assert recording_path.exists() is False

        def write_data_pickle():
            with recording_path.open(mode='wb') as fobj:
                for packet in asn1_recording_data:
                    data = pickle.dumps(packet, protocol=4)
                    fobj.write(data)

        def read_data_pickle():
            with recording_path.open(mode='rb') as fobj:
                l = []
                for i in range(0, 2):
                    decoded = pickle.load(fobj)
                    l.append(decoded)
                return l

        def do_all():
            write_data_pickle()
            return read_data_pickle()

        packets = benchmark(do_all)
        assert len(recording_path.read_bytes()) == 490
        assert packets == asn1_recording_data

    @pytest.mark.asyncio
    async def test_01_recording(self, asn1_recording_data, tmpdir, benchmark, context):
        recording_path = Path(tmpdir / 'recording.pickle')

        def write_data_recording():
            with recording_path.open(mode='wb') as fobj:
                for packet in asn1_recording_data:
                    data = packet['data']
                    obj = BufferObject(data, context=context)
                    data = obj.record
                    fobj.write(data)

        def read_data_recording():
            return list(Record.from_file(Path(recording_path)))

        def do_all():
            write_data_recording()
            return read_data_recording()

        packets = benchmark(do_all)

        asn1_recording_data[0]['seconds'] = packets[0]['seconds']
        asn1_recording_data[1]['seconds'] = packets[1]['seconds']
        assert len(recording_path.read_bytes()) == 372
        assert packets == asn1_recording_data


class TestWriteRecording:
    @pytest.mark.asyncio
    async def test_00_pickle_write(self, asn1_recording_data, tmpdir, pickle_codec, benchmark):
        recording_path = Path(tmpdir / 'recording.pickle')

        def write_data_pickle(fobj):
            for packet in asn1_recording_data:
                data = pickle.dumps(packet, protocol=4)
                fobj.write(data)

        with recording_path.open(mode='wb') as fobj:
            benchmark(write_data_pickle, fobj)

    @pytest.mark.asyncio
    async def test_01_recording(self, asn1_recording_data, tmpdir, benchmark, context):
        recording_path = Path(tmpdir / 'recording.pickle')

        def write_data_recording(fobj):
            for packet in asn1_recording_data:
                data = packet['data']
                obj = BufferObject(data, context=context)
                data = obj.record
                fobj.write(data)

        with recording_path.open(mode='wb') as fobj:
            benchmark(write_data_recording, fobj)


class TestReadRecording:
    @pytest.mark.asyncio
    async def test_00_pickle(self, asn1_recording_data, tmpdir, pickle_codec, benchmark):
        recording_path = Path(tmpdir / 'recording.pickle')

        with recording_path.open(mode='wb') as fobj:
            for packet in asn1_recording_data:
                data = pickle.dumps(packet, protocol=4)
                fobj.write(data)

        def read_data_pickle(fobj):
            fobj.seek(0)
            l = []
            for i in range(0, 2):
                decoded = pickle.load(fobj)
                l.append(decoded)
            return l

        with recording_path.open(mode='rb') as fobj:
            packets = benchmark(read_data_pickle, fobj)
        assert packets == asn1_recording_data

    @pytest.mark.asyncio
    async def test_01_recording(self, asn1_recording_data, tmpdir, benchmark, context):
        recording_path = Path(tmpdir / 'recording.pickle')

        with recording_path.open(mode='ab') as fobj:
            for packet in asn1_recording_data:
                data = packet['data']
                obj = BufferObject(data, context=context)
                data = obj.record
                fobj.write(data)

        def read_data_recording(fobj):
            fobj.seek(0)
            return list(Record.from_file(fobj))

        with recording_path.open(mode='rb') as fobj:
            packets = benchmark(read_data_recording, fobj)

        asn1_recording_data[1]['seconds'] = 0.0
        assert packets == asn1_recording_data
