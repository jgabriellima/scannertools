import pytest
import scannertools as st
import scannertools.object_detection as object_detection
import scannertools.face_detection as face_detection
import scannertools.optical_flow as optical_flow
import scannertools.shot_detection as shot_detection
import scannertools.pose_detection as pose_detection
import scannertools.gender_detection as gender_detection
import scannertools.face_embedding as face_embedding
import scannerpy
import os
import subprocess as sp
import tempfile
import toml
import shutil

try:
    sp.check_call(['nvidia-smi'])
    has_gpu = True
except (OSError, sp.CalledProcessError):
    has_gpu = False

needs_gpu = pytest.mark.skipif(not has_gpu, reason='need GPU to run')


@pytest.fixture(scope='module')
def video():
    with st.sample_video() as video:
        yield video


@pytest.fixture(scope='module')
def audio(video):
    audio = video.audio()
    yield audio
    os.remove(audio.path())


@pytest.fixture(scope='module')
def db():
    cfg = scannerpy.Config.default_config()
    cfg['network']['master'] = 'localhost'
    cfg['storage']['db_path'] = tempfile.mkdtemp()

    with tempfile.NamedTemporaryFile() as cfg_f:
        cfg_f.write(bytes(toml.dumps(cfg), 'utf-8'))
        cfg_f.flush()

        with scannerpy.Database(config_path=cfg_f.name) as db:
            yield db

    shutil.rmtree(cfg['storage']['db_path'])


def test_frame(video):
    frame = video.frame(0)
    assert frame.shape == (video.height(), video.width(), 3)


def test_metadata(video):
    video.fps()
    video.num_frames()
    video.duration()


def test_frame_time(video):
    video.frame(number=10)
    video.frame(time=10)


def test_frames(video):
    frames = video.frames([1, 1, 0])
    assert len(frames) == 3


def test_audio(video, audio):
    path = audio.extract()
    assert os.path.isfile(path)
    os.remove(path)


def test_object_detection(db, video):
    [bboxes] = object_detection.detect_objects(db, videos=[video], frames=[[0]])
    assert len([bb for bb in next(bboxes.load()) if bb.score > 0.5]) == 1


def test_face_detection(db, video):
    [bboxes] = face_detection.detect_faces(db, videos=[video], frames=[[0]])
    assert len([bb for bb in next(bboxes.load()) if bb.score > 0.5]) == 1


def test_gender_detection(db, video):
    bboxes = face_detection.detect_faces(db, videos=[video], frames=[[0]])
    genders = gender_detection.detect_genders(db, videos=[video], frames=[[0]], bboxes=bboxes)
    next(genders[0].load())
    # TODO: test output


def test_face_embedding(db, video):
    bboxes = face_detection.detect_faces(db, videos=[video], frames=[[0]])
    embeddings = face_embedding.embed_faces(db, videos=[video], frames=[[0]], bboxes=bboxes)
    next(embeddings[0].load())
    # TODO: test output


def test_montage(video):
    video.montage([0, 1], cols=2)


def test_optical_flow(db, video):
    optical_flow.compute_flow(db, videos=[video], frames=[[1]])


def test_shot_detection(db, video):
    shot_detection.detect_shots(db, videos=[video])


@needs_gpu
def test_pose_detection(db, video):
    pose_detection.detect_poses(db, video, frames=[0])
