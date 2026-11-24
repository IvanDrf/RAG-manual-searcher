from functools import cache
from pathlib import Path
from threading import Lock

import numpy as np


class InvalidTeacherPhoto(ValueError):
    """The uploaded file could not be decoded as an image."""


class FaceClassificator:
    def fit(self, X: np.ndarray, y: np.ndarray):
        self.X_train = X
        self.y_train = y
        return self

    def predict(self, X: np.ndarray):
        similarities = X @ self.X_train.T
        best_indices = np.argmax(similarities, axis=1)
        return self.y_train[best_indices], similarities[np.arange(len(X)), best_indices]


_model_lock = Lock()


@cache
def _load_models():
    from insightface.app import FaceAnalysis
    from onnxruntime import SessionOptions

    options = SessionOptions()
    options.intra_op_num_threads = 2

    detector = FaceAnalysis(
        name="buffalo_s",
        allowed_modules=["detection", "recognition"],
        providers=["CPUExecutionProvider"],
        sess_options=options,
    )
    detector.prepare(ctx_id=-1, det_size=(320, 320))

    with np.load(Path(__file__).with_name("teacher.npz")) as data:
        classifier = FaceClassificator().fit(data["embeding"], data["labels"])
    return detector, classifier


def predict_teacher(path_image: str | Path) -> str | None:
    import cv2

    image = cv2.imread(str(path_image))
    if image is None:
        raise InvalidTeacherPhoto("Не удалось открыть фото.")

    with _model_lock:
        detector, classifier = _load_models()
        faces = detector.get(image)

    if not faces:
        return None

    main_face = max(
        faces,
        key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]),
    )
    predictions, _ = classifier.predict(main_face.normed_embedding.reshape(1, -1))
    return str(predictions[0]).replace("_", " ")
