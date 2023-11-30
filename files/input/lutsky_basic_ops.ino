#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>

//tds vars
#define TdsSensorPin A1
#define VREF 5.0 // analog reference voltage(Volt) of the ADC
#define SCOUNT 10 // sum of sample point
int analogBuffer[SCOUNT]; // store the analog value in the array, read from ADC
int analogBufferTemp[SCOUNT];
int analogBufferIndex = 0,copyIndex = 0;
float averageVoltage = 0,tdsValue = 0,temperature = 25;

//envelope vars
int analog_pin = A0;
int tx_pin = 2;
int led = 5;
long previousMillis = 0;
long interval = 500;
long initial_time;

LiquidCrystal_PCF8574 lcd(0x27);

void setup() {
  Serial.begin(115200);

  //envelope setup
  pinMode(tx_pin, OUTPUT);  //Pin 4 provides the voltage step
  pinMode(led, OUTPUT);
  initial_time = millis();

  //tds setup
  pinMode(TdsSensorPin,INPUT);

  //lcd setup
  int error;
  Serial.println("LCD...");
  // wait on Serial to be available on Leonardo
  while (!Serial)
    ;
  Serial.println("Probing for PCF8574 on address 0x27...");

  // See http://playground.arduino.cc/Main/I2cScanner how to test for a I2C device.
  Wire.begin();
  Wire.beginTransmission(0x27);
  error = Wire.endTransmission();
  Serial.print("Error: ");
  Serial.print(error);

  if (error == 0) {
    Serial.println(": LCD found.");
    lcd.begin(16, 2);  // initialize the lcd
  } else {
    Serial.println(": LCD not found.");
  } 
  printLcd("Welcome!");
}

void loop() {
  int open = getEnvelopeState();
  unsigned long currentMillis;
  while(!open) {
    currentMillis = millis();
    if(currentMillis - previousMillis > interval) {
      previousMillis = currentMillis;
      open = getEnvelopeState();
    }
  }
  if(open) {
    int procrastination = (millis() - initial_time) / 1000;
    printLcd("You opened the letter! It took you " + String(procrastination) + " years. What does it say? Is it sad? Are those tears?");
  }
  int tears = getPPM();
  while (!tears) {
    currentMillis = millis();
    if(currentMillis - previousMillis > interval) {
      previousMillis = currentMillis;   
      tears = getPPM();
    }
  }
  if (tears) {
    printLcd("Tears! Finally you show some emotion!");
  }  
  exit(0);
}

int getPPM(){
  static unsigned long analogSampleTimepoint = millis();
  if(millis()-analogSampleTimepoint > 40U) { //every 40 milliseconds,read the analog value from the ADC
    analogSampleTimepoint = millis();
    analogBuffer[analogBufferIndex] = analogRead(TdsSensorPin); //read the analog value and store into the buffer
    analogBufferIndex++;
    if(analogBufferIndex == SCOUNT)
      analogBufferIndex = 0;
  }
  static unsigned long printTimepoint = millis();
  if(millis()-printTimepoint > 800U) {
    printTimepoint = millis();
    for(copyIndex=0;copyIndex<SCOUNT;copyIndex++)
      analogBufferTemp[copyIndex]= analogBuffer[copyIndex];
    averageVoltage = getMedianNum(analogBufferTemp,SCOUNT) * (float)VREF/ 1024.0; // read the analog value more stable by the median filtering algorithm, and convert to voltage value
    float compensationCoefficient=1.0+0.02*(temperature-25.0); //temperature compensation formula: fFinalResult(25^C) = fFinalResult(current)/(1.0+0.02*(fTP-25.0));
    float compensationVolatge=averageVoltage/compensationCoefficient; //temperature compensation
    tdsValue=(133.42*compensationVolatge*compensationVolatge*compensationVolatge - 255.86*compensationVolatge*compensationVolatge + 857.39*compensationVolatge)*0.5; //convert voltage value to tds value
    //Serial.print("voltage:");
    //Serial.print(averageVoltage,2);
    //Serial.print("V ");
    Serial.print("TDS Value:");
    Serial.print(tdsValue);
    Serial.println("ppm");
    return (tdsValue > 330);
  }
}
int getMedianNum(int bArray[], int iFilterLen) {
  int bTab[iFilterLen];
  for (byte i = 0; i<iFilterLen; i++)
  bTab[i] = bArray[i];
  int i, j, bTemp;
  for (j = 0; j < iFilterLen - 1; j++) {
    for (i = 0; i < iFilterLen - j - 1; i++) {
      if (bTab[i] > bTab[i + 1]) {
        bTemp = bTab[i];
        bTab[i] = bTab[i + 1];
        bTab[i + 1] = bTemp;
      }
    }
  }
  if ((iFilterLen & 1) > 0)
    bTemp = bTab[(iFilterLen - 1) / 2];
  else
    bTemp = (bTab[iFilterLen / 2] + bTab[iFilterLen / 2 - 1]) / 2;
  return bTemp;
}
int printLcd(String txt) {
  int maxLength = 16;
  int index = 0;
  int end_index;
  char chars[txt.length()];
  txt.toCharArray(chars, txt.length());
  lcd.setBacklight(255);
  lcd.clear();
  lcd.home();
  while (index <= txt.length()) {
    lcd.clear();
    lcd.home();    
    end_index = index + maxLength;
    lcd.print(txt.substring(index, end_index));
    Serial.println(txt.substring(index, end_index));
    index = end_index;
    end_index = index + maxLength;
    lcd.setCursor(0, 1);
    lcd.print(txt.substring(index, end_index));
    Serial.println(txt.substring(index, end_index));
    index = end_index;
    delay(2000);
  }
}
int getEnvelopeState() {  // Function to execute rx_tx algorithm and return a value
                           // that depends on coupling of two electrodes.
                           // returns 0 for open, 1 for closed.
  int read_high;
  int read_low;
  int diff;
  long int sum;
  int N_samples = 100; // Number of samples to take.  Larger number slows it down, but reduces scatter.
  int threshhold = 30;

  sum = 0;

  for (int i = 0; i < N_samples; i++) {
    digitalWrite(tx_pin, HIGH);          // Step the voltage high on conductor 1.
    read_high = analogRead(analog_pin);  // Measure response of conductor 2.
    digitalWrite(tx_pin, LOW);           // Step the voltage to zero on conductor 1.
    read_low = analogRead(analog_pin);   // Measure response of conductor 2.
    diff = read_high - read_low;         // desired answer is the difference between high and low.
    sum += diff;                         // Sums up N_samples of these measurements.
  }
  Serial.println(sum/N_samples);
  Serial.println("open?");
  Serial.println(sum/N_samples < 35);

  return (sum/N_samples < 35);
}  