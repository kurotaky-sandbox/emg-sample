import processing.serial.*;
import controlP5.*;
import java.util.Date;
import java.text.SimpleDateFormat;

ControlP5 cp5;
Chart chart_emg1;
final int NUM_GRAPH_DATA = 200;
Serial myPort;
SensorData m_sensor_data;

void setup()
{
  size(800, 400);
  String portName = Serial.list()[3];
  println(portName);
  myPort = new Serial(this, portName, 115200);

  frameRate(300);

  cp5 = new ControlP5(this);
  
  // グラフ設定
  chart_emg1 = cp5.addChart("ch1");
  chart_emg1.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(700, 300)                               /* グラフの表示サイズ */
           .setPosition(10, 50)                          /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .getColor().setBackground(color(14, 39, 58)); /* グラフの背景色を設定する */
  setupChartAttr(chart_emg1, "ch1", color(200, 0, 192));
}

void serialEvent(Serial myPort) { 
   String mystring = myPort.readStringUntil('\n');
   if (mystring != null) {
       mystring = trim(mystring);
       SensorData s_data = new SensorData();
       s_data.setPacket(float(split(mystring, ",")));
       m_sensor_data = s_data;
   }
}

void draw()
{
  background(#000000);

  if (m_sensor_data != null)
  {
    chart_emg1.unshift("ch1", m_sensor_data.ch1);
    fill(0);
    textSize(22);
    textAlign(CENTER);
    text("time: " + m_sensor_data.time, 100, 35);
    print(m_sensor_data.ch1);
  }
}

void setupChartAttr(Chart chart, String axis_name, int col)
{
  chart.addDataSet(axis_name);
  chart.setData(axis_name, new float[NUM_GRAPH_DATA]);
  chart.setColors(axis_name, col, color(255,255,128));
  chart.setStrokeWeight(1.5);
}


class SensorData
{
  float time;
  float ch1;

  void setPacket(float[] packet)
  {
    if (packet.length < 3)
    {
      return;
    }
    time = packet[0];
    ch1 = packet[1];
  }
};
