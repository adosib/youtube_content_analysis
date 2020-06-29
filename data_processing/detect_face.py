import cv2
import requests
import tempfile
import numpy as np
from mtcnn import MTCNN

CLASSIFIER = cv2.CascadeClassifier(cv2.data.haarcascades +
                                   "haarcascade_frontalface_default.xml")


def get_image(img_path):
    """
    Fetches an image from a URL and returns the image represented as a numpy ndarray
    """
    # retrieve the image from the img_path url
    r = requests.get(img_path)

    # save the image to a temp file
    jpg = tempfile.NamedTemporaryFile(mode="wb")
    jpg.write(r.content)

    img = cv2.imread(jpg.name)  # load the image from the temp file
    #img = rotate_bound(img, 180)

    jpg.close()  # destroy the temp file

    return img


def detect_face_v1(img_path, classifier=CLASSIFIER) -> tuple:
    """
    Detects whether or not a face is present in an image using Haar cascades.
    Returns a tuple with the bool and the output of the detectMultiScale method.
    """
    img = get_image(img_path)

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # grayscale img

    # detectMultiScale returns the positions of detected faces as Rect(x,y,w,h)
    face = classifier.detectMultiScale(
        img_gray, scaleFactor=1.3, minNeighbors=4
    )

    try:
        if face.any():
            return (True, face)

    except AttributeError:
        return (False,)


def detect_face_v2(img_path) -> tuple:
    """
    Detects whether or not a face is present in an image using a (pretrained) CNN.
    Returns a tuple with the bool and the output of the detect_faces method.
    """
    img = get_image(img_path)

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    detector = MTCNN()
    face = detector.detect_faces(img)

    if face:
        return (True, face)
    return (False,)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Detects if a face is present in an image'
    )
    parser.add_argument(
        '-img', '--image_path', required=True, type=str, help='path to an image'
    )
    parser.add_argument(
        '-v', '--algo_version', default=2, type=int, help='select a version of the face detection algo (1 or 2)'
    )
    args = parser.parse_args()

    img_path = args.image_path

    face = detect_face_v1(img_path)
    if args.algo_version == 2:
        face = detect_face_v2(img_path)

    print("Image contains face: {}".format(face[0]))

    try:
        # get the image
        img = get_image(img_path)
        # draw rectangle around the face(s)
        for detected in face[1]:  # for every detected face
            print("confidence: {}".format(detected['confidence']))
            for (column, row, width, height) in [detected['box']]:
                img = cv2.rectangle(
                    img,
                    (column, row),
                    (column + width, row + height),
                    (0, 255, 0),
                    2
                )
    except Exception as e:
        print(e)
        pass
    finally:
        cv2.imshow('img', img)

        wait_time = 1000
        while cv2.getWindowProperty('img', cv2.WND_PROP_VISIBLE) >= 1:
            keyCode = cv2.waitKey(wait_time)
            if (keyCode & 0xFF) == ord("q"):
                cv2.destroyAllWindows()
                break
