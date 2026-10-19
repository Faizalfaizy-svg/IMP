from rplidar import RPLidar

lidar = RPLidar('/dev/ttyUSB0')
print(lidar.get_info())
print(lidar.get_health())

for i, scan in enumerate(lidar.iter_scans()):
    print(len(scan), "points")
    if i > 10:
        break

lidar.stop()
lidar.stop_motor()
lidar.disconnect()