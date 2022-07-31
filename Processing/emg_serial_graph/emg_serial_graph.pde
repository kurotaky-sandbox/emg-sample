import processing.serial.*;
import controlP5.*;

ControlP5 cp5;
Chart chart_emg;
final int NUM_GRAPH_DATA = 200;

void setup()
{
  size(650, 700);

  String portName = Serial.list()[3];
  println(portName);
  Serial m_myPort = new Serial(this, portName, 115200);

  frameRate(200);

  cp5 = new ControlP5(this);
  
  // グラフ設定
  chart_emg = cp5.addChart("EMG Sensor");
  chart_emg.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(-20000, 20000)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 200)                               /* グラフの表示サイズ */
           .setPosition(10, 250)                            /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .setStrokeWeight(1.5)                            /* グラフの線の太さを設定する */
           .getColor().setBackground(color(224, 224, 224));  /* グラフの背景色を設定する */
           
  setupChartAttr(chart_emg, "ch1", color(0, 0, 192));
  setupChartAttr(chart_emg, "ch2", color(192, 0, 0));
  setupChartAttr(chart_emg, "ch3", color(0, 192, 0));
}

void setupChartAttr(Chart chart, String axis_name, int col)
{
  chart.addDataSet(axis_name);
  chart.setData(axis_name, new float[NUM_GRAPH_DATA]);
  chart.setColors(axis_name, col, color(255,255,128));
}
