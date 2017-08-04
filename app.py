import eventlet
import json
import math

from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap


eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET'] = 'my secret key'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MQTT_BROKER_URL'] = 'ip.for.raspberry.pi.broker.goes.here'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''
app.config['MQTT_PASSWORD'] = ''
app.config['MQTT_KEEPALIVE'] = 30
app.config['MQTT_TLS_ENABLED'] = False
app.config['MQTT_LAST_WILL_TOPIC'] = 'pyohio/thick_client/lastwill'
app.config['MQTT_LAST_WILL_MESSAGE'] = 'IF YOU ARE READING THIS, I AM DEAD.'
app.config['MQTT_LAST_WILL_QOS'] = 2

# Parameters for SSL enabled
# app.config['MQTT_BROKER_PORT'] = 8883
# app.config['MQTT_TLS_ENABLED'] = True
# app.config['MQTT_TLS_INSECURE'] = True
# app.config['MQTT_TLS_CA_CERTS'] = 'ca.crt'

mqtt = Mqtt(app)
socketio = SocketIO(app)
bootstrap = Bootstrap(app)


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('publish')
def handle_publish(json_str):
    data = json.loads(json_str)
    mqtt.publish(topic=data['topic'], payload=data['message'], qos=0, retain=False)


@socketio.on('subscribe')
def handle_subscribe(json_str):
    data = json.loads(json_str)
    subscribe_to_topic(topic=data['topic'], qos=0)


@mqtt.on_topic('pyohio/+/knob/+/value')
def translate_knob_values_to_led_values(client, userdata, message):
    knob_value = message.payload.decode()
    try:
        valid_knob_value = int(knob_value)
        message = translate_knob_values(valid_knob_value)
        publish_message(topic='led_string/gauge', payload=message, qos=0, retain=True)
    except ValueError:
        print("VALUE ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!")


@mqtt.on_topic('pyohio/+/button/+/value')
def translate_button_values_to_led_values(client, userdata, message):
    button_value = message.payload.decode()
    try:
        color_to_send = translate_color_values(button_value)
        print("PUBLISHING: {}".format(color_to_send))
        publish_message(topic='led_string/color', payload=color_to_send, qos=0, retain=True)
    except TypeError:
        print("TYPE ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")


def translate_knob_values(knob_value):
    return_value = None
    range_value = 20
    num_of_leds_to_light = 0
    while not return_value:
        if knob_value <= range_value:
            return_value = num_of_leds_to_light
        else:
            range_value += 20
            num_of_leds_to_light += 1
    return_value = num_of_leds_to_light if num_of_leds_to_light <= 50 else 50
    return return_value


def translate_color_values(color):
    if color == 'RED':
        color_tuple = '(0, 255, 0)'
    elif color == 'BLUE':
        color_tuple = '(0, 0, 255)'
    elif color == 'GREEN':
        color_tuple = '(255, 0, 0)'
    else:
        color_tuple = '(255, 255, 255)'
    return color_tuple


# @mqtt.on_message()
# def handle_mqtt_message(client, userdata, message):
#     topic = message.topic
#     msg = message.payload.decode()
#     do cool stuff here, but avoid giant if-else blocks with @mqtt.on_topic decorators.


def emit_data_to_frontend(msg, topic):
    data = dict(topic=topic, payload=msg)
    socketio.emit('mqtt_message', data=data)


def subscribe_to_topic(topic, qos=0):
    mqtt.subscribe(topic=topic, qos=qos)


def publish_message(topic, payload, qos=0, retain=False):
    mqtt.publish(topic=topic, payload=payload, qos=qos, retain=retain)


@mqtt.on_log()
def handle_logging(client, userdata, level, buf):
    print(level, buf)


if __name__ == '__main__':
    print("SUBSCRIBING TO BASE TOPIC")
    subscribe_to_topic('pyohio/#')
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=True, debug=True)
