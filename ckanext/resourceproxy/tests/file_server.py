from flask import Flask
import os

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(
                os.path.realpath( __file__ )),
                                       "static")
           )


@app.route("/", methods=['GET', 'POST'])
def ok():
    return 'ok'

if __name__ == "__main__":
    app.run(port=50001)
