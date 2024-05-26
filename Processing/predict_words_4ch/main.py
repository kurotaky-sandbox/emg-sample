from flask import Flask, request, jsonify
import numpy as np
import tensorflow as tf
import librosa

app = Flask(__name__)

# Load pre-trained TensorFlow model
#model = tf.keras.models.load_model('your_model_path.h5')

@app.route('/process_data', methods=['POST'])
def process_data():
    data = request.json
    sensor_data = np.array([[d['ch1'], d['ch2'], d['ch3'], d['ch4']] for d in data])

    # Perform MFCC transformation
    #mfccs = []
    #for row in sensor_data:
    #    mfcc = librosa.feature.mfcc(y=row, sr=16000, n_mfcc=13)
    #    mfccs.append(mfcc)
    
    #mfccs = np.array(mfccs)

    # Model prediction
    # predictions = model.predict(mfccs)
    
    # Convert predictions to labels (assuming a classification task)
    # labels = np.argmax(predictions, axis=1)


    # ここで判定結果を返す
    response = {
        "result": "start"
    }
    print(sensor_data)
    
    return jsonify(response)
    # return jsonify(sensor_data.tolist())
    # return jsonify(labels.tolist())

if __name__ == '__main__':
    app.run(debug=True)
