# Atlas Copco Compressor Monitoring System

## Description
This project implements a monitoring system for Atlas Copco GA90VP_16 air compressors. The system collects operational data from multiple compressors through their web interfaces and stores it in InfluxDB for visualization and analysis in Grafana.

## Features
- Real-time monitoring of multiple compressors
- Automatic data collection from compressor web interfaces
- Support for different compressor generations
- Data storage in InfluxDB for time-series analysis
- Integration with Grafana for visualization
- Comprehensive logging system
- Automatic error handling and reporting

## Monitored Parameters
The system collects various parameters from each compressor:

### Analog Inputs (AI)
- Compressor Outlet Pressure
- Element Outlet Temperature
- Ambient Air Temperature
- Controller Temperature (Type 2 only)
- Relative Humidity (Type 2 only)
- Vessel Pressure (Type 2 only)

### Counters (CNT)
- Running Hours
- Motor Starts
- Load Relay Count
- Fan Starts
- Accumulated Volume
- Module Hours
- Low Load Hours (Type 1)
- Loaded Hours (Type 2)
- Emergency Stops (Type 2)
- Direct Stops (Type 2)

### Variable Frequency Drive (VFD)
- Rotation Speed
- Current
- Flow Percentage

### Digital Inputs (DI)
- Emergency Stop
- Overload Fan Motor
- Electronic Condensate Drain
- Pressure Setting Selection
- Active Power Supply (Type 2)
- Phase Sequence (Type 2)
- Air Filter (Type 2)

### Digital Outputs (DO)
- Fan Motor
- Blowoff
- General Shutdown
- Automatic Operation
- General Warning
- Run Enable Main Motor
- Recirculation Valve (Type 2)
- Cubicle Fan (Type 2)

### Status Parameters (SP)
- No Valid Pressure Control
- Motor Converter 1 Alarm
- Expansion Module Communication
- Low Load Alarm (Type 1)

### Machine State (MS)
- Primary State

## Prerequisites
- Python 3.8 or higher
- InfluxDB server
- Network access to compressors
- Required Python packages:
  - requests
  - pytz
  - influxdb-client

## Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/atlas_copco.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the InfluxDB connection:
   - Update `_IP_INFLUXDB` in the script with your InfluxDB server address
   - Ensure the database 'COMPRESSORS' exists in your InfluxDB instance

## Usage
1. Configure the compressor list in the `_COMPRESSORS` array:
   ```python
   _COMPRESSORS = [
       ['IP_ADDRESS', 'TAG', 'LOCATION', TYPE],
       # Example:
       ['10.100.58.30', '080BL515', 'Compressor Room', 1]
   ]
   ```

2. Run the script:
   ```bash
   python compressor_web_stat.py
   ```

3. View the data in Grafana:
   - Connect Grafana to your InfluxDB instance
   - Create dashboards using the collected metrics

## Logging
The system maintains detailed logs in the `compressors.log` file, including:
- Connection status
- Data collection results
- Error messages
- Debug information (when enabled)

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
- Atlas Copco for the compressor equipment
- InfluxDB and Grafana for data storage and visualization
- All contributors who have helped shape this project
