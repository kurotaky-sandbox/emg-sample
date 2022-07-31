import processing.serial.*;
import controlP5.*;

ControlP5 cp5;
Chart chart_emg1, chart_emg2, chart_emg3;
final int NUM_GRAPH_DATA = 200;
Serial myPort;
SensorData m_sensor_data;

void setup()
{
  size(800, 800);
  String portName = Serial.list()[3];
  println(portName);
  myPort = new Serial(this, portName, 115200);

  frameRate(300);

  cp5 = new ControlP5(this);
  
  // グラフ設定
  chart_emg1 = cp5.addChart("ch1");
  chart_emg1.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 200)                               /* グラフの表示サイズ */
           .setPosition(10, 0)                            /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .setStrokeWeight(5.0)                            /* グラフの線の太さを設定する */
           .getColor().setBackground(color(224, 224, 224));  /* グラフの背景色を設定する */
           
  setupChartAttr(chart_emg1, "ch1", color(0, 0, 192));
  
  chart_emg2 = cp5.addChart("ch2");
  chart_emg2.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 200)                               /* グラフの表示サイズ */
           .setPosition(10, 250)                            /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .setStrokeWeight(5.0)                            /* グラフの線の太さを設定する */
           .getColor().setBackground(color(224, 224, 224));  /* グラフの背景色を設定する */
  
  setupChartAttr(chart_emg2, "ch2", color(192, 0, 0));
  
  chart_emg3 = cp5.addChart("ch3");
  chart_emg3.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 200)                               /* グラフの表示サイズ */
           .setPosition(10, 500)                            /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .setStrokeWeight(5.0)                            /* グラフの線の太さを設定する */
           .getColor().setBackground(color(224, 224, 224));  /* グラフの背景色を設定する */
  
  
  setupChartAttr(chart_emg3, "ch3", color(0, 192, 0));
}

void serialEvent(Serial myPort) { 
   String mystring = myPort.readStringUntil('\n');
   if (mystring != null) {
       //println(mystring);
       mystring = trim(mystring);
       SensorData s_data = new SensorData();
       s_data.setPacket(float(split(mystring, ",")));
       m_sensor_data = s_data;
   }
}

void draw()
{
  background(#EEEEEE);

  if (m_sensor_data != null)
  {
    chart_emg1.unshift("ch1", m_sensor_data.ch1);
    chart_emg2.unshift("ch2", m_sensor_data.ch2);
    chart_emg3.unshift("ch3", m_sensor_data.ch3);
  }
}

void setupChartAttr(Chart chart, String axis_name, int col)
{
  chart.addDataSet(axis_name);
  chart.setData(axis_name, new float[NUM_GRAPH_DATA]);
  chart.setColors(axis_name, col, color(255,255,128));
}


class SensorData
{
  float time;
  float ch1, ch2, ch3;

  void setPacket(float[] packet)
  {
    if (packet.length < 3)
    {
      return;
    }
    time = packet[0];
    ch1 = packet[1];
    ch2 = packet[2];
    ch3 = packet[3];
  }
};
