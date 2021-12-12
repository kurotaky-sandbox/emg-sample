#define n 50 //標本数を決める

int f[n]={0};
float ave = 0;      //平均値を入れる変数

void setup(){
    Serial.begin(9600);
}

void loop(){
    for(int i = n-1; i > 0; i--) {
      f[i] = f[i-1];//過去n回分の値を記録
    }
    f[0] = analogRead(0);
    ave = 0;

    for(int i = 0; i < n; i++) {
      ave += f[i];        //総和を求める
    }
    ave = (float)ave/n;                  //標本数で割って平均を求める

    Serial.print(f[0]);                  //フィルタ前の値
    Serial.print(",");
    Serial.print(ave);                   //フィルタ後の値
    Serial.print("\n");
}
