import cv2
import requests
import tempfile

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

    jpg.close()  # destroy the temp file

    return img


def detect_face(img_path, classifier=CLASSIFIER) -> tuple:
    """
    Detects whether or not a face is present in an image.
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Detects if a face is present in an image'
    )
    parser.add_argument(
        '-img', '--image_path', required=True, type=str, help='path to an image'
    )
    args = parser.parse_args()

    img_path = args.image_path

    face = detect_face(img_path)
    print("Image contains face: {}".format(face[0]))

    try:
        # get the image
        gray_image = get_image(img_path)
        # draw rectangle around the face(s)
        for (column, row, width, height) in face[1]:
            cv2.rectangle(
                gray_image,
                (column, row),
                (column + width, row + height),
                (0, 255, 0),
                2
            )
    except:
        pass
    finally:
        cv2.imshow('img', gray_image)

        wait_time = 1000
        while cv2.getWindowProperty('img', cv2.WND_PROP_VISIBLE) >= 1:
            keyCode = cv2.waitKey(wait_time)
            if (keyCode & 0xFF) == ord("q"):
                cv2.destroyAllWindows()
                break
