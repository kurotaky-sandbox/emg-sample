import processing.serial.*;
import controlP5.*;
import java.util.Date;
import java.text.SimpleDateFormat;

ControlP5 cp5;
Chart chart_emg1, chart_emg2, chart_emg3, chart_emg4;
final int NUM_GRAPH_DATA = 200;
Serial myPort;
SensorData m_sensor_data;
PrintWriter file;

void setup()
{
  file = createWriter("output/" + timestamp() + ".csv");
  file.println("time,ch1,ch2,ch3,ch4");
  size(800, 800);
  String portName = Serial.list()[2];
  println(portName);
  myPort = new Serial(this, portName, 230400); //115200

  frameRate(300);

  cp5 = new ControlP5(this);

  // グラフ設定
  chart_emg1 = cp5.addChart("ch1");
  chart_emg1.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 100)                               /* グラフの表示サイズ */
           .setPosition(10, 50)                          /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .getColor().setBackground(color(224, 224, 224)); /* グラフの背景色を設定する */

  setupChartAttr(chart_emg1, "ch1", color(0, 0, 192));
  
  chart_emg2 = cp5.addChart("ch2");
  chart_emg2.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 100)                               /* グラフの表示サイズ */
           .setPosition(10, 200)                            /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .getColor().setBackground(color(224, 224, 224));  /* グラフの背景色を設定する */
  
  setupChartAttr(chart_emg2, "ch2", color(192, 0, 0));
  
  chart_emg3 = cp5.addChart("ch3");
  chart_emg3.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 100)                               /* グラフの表示サイズ */
           .setPosition(10, 350)                            /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .getColor().setBackground(color(224, 224, 224));  /* グラフの背景色を設定する */
           
  setupChartAttr(chart_emg3, "ch3", color(0, 192, 0));
  
  chart_emg4 = cp5.addChart("ch4");
  chart_emg4.setView(Chart.LINE)                             /* グラフの種類（折れ線グラフ） */
           .setRange(0, 3.5)                         /* 値の範囲（最小値、最大値） */
           .setSize(600, 100)                               /* グラフの表示サイズ */
           .setPosition(10, 500)                            /* グラフの表示位置 */
           .setColorCaptionLabel(color(0,0,255))            /* キャプションラベルの色 */
           .getColor().setBackground(color(224, 224, 224));  /* グラフの背景色を設定する */
           
  setupChartAttr(chart_emg4, "ch4", color(192, 192, 0));
}

void serialEvent(Serial myPort) { 
    try {
        String mystring = myPort.readStringUntil('\n');
        // float mtime =  float(millis()); //float(ms);

        if (mystring != null) {
            mystring = trim(mystring);
            int value1 = unhex(mystring.substring(0, 3));
            int value2 = unhex(mystring.substring(3, 6));
            int value3 = unhex(mystring.substring(6, 9));
            int value4 = unhex(mystring.substring(9, 12));
            int count = unhex(mystring.substring(12, 16));
                 
            float v1 = value1 * 3.3 / 1023;
            float v2 = value2 * 3.3 / 1023;
            float v3 = value3 * 3.3 / 1023;
            float v4 = value4 * 3.3 / 1023;

            float[] data =  new float[5];
            data[0] = count;
            data[1] = v1;
            data[2] = v2;
            data[3] = v3;
            data[4] = v4;
         
            SensorData s_data = new SensorData();
            s_data.setPacket(data);
            m_sensor_data = s_data;
            file.println(m_sensor_data.count + "," + m_sensor_data.ch1 + "," + m_sensor_data.ch2 + "," + m_sensor_data.ch3 + "," + m_sensor_data.ch4);
        }
    } catch(Exception e) {
         e.printStackTrace();
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
    chart_emg4.unshift("ch4", m_sensor_data.ch4);
    fill(0);
    textSize(22);
    textAlign(CENTER);
    text("count: " + m_sensor_data.count, 100, 35);
  }
}

void setupChartAttr(Chart chart, String axis_name, int col)
{
  chart.addDataSet(axis_name);
  chart.setData(axis_name, new float[NUM_GRAPH_DATA]);
  chart.setColors(axis_name, col, color(255,255,128));
  chart.setStrokeWeight(2.5);
}


class SensorData
{
  float count;
  float ch1, ch2, ch3, ch4;

  void setPacket(float[] packet)
  {
    if (packet.length < 4)
    {
      return;
    }
    count = packet[0];
    ch1 = packet[1];
    ch2 = packet[2];
    ch3 = packet[3];
    ch4 = packet[4];
    
  }
};

String timestamp() {
  Date date = new Date();
  SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd-HHmmss");
  return sdf.format(date);
}
