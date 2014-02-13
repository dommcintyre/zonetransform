A user reported problems with zone-based .tcx workouts and the Forerunner
620 on the Garmin forums.
This Python program uses an xml parser to scan a workout file for targets
using zones and convert them to custom paces, based on pace zone values
entered by the user.
To use, execute zonetransform.py with python zonetransform.py
Press Set Zones to adjust the zones. These are constrained to be contiguous,
non-overlapping zones. Enter the lower limit of each zone, and the upper limit
of the top zone. Select whether you are entering paces as min/mi or min/km.
Click OK.
If you wish to save the zones as defaults, click Save Zones as Default.
The program will save them in the ztconfig.cfg file in the same directory as
zonetransform.py, and reload them automatically at restart.
Click Run and select the file you wish to convert. It can contain one or many
workouts. 
If no zone targets are found, nothing is done.
If zone targets are found, they are converted to custom paces, and ViewAs set
to pace for Running workouts and speed otherwise. cz (for 'custom zone') is 
appended to the name of each workout within the tcx file, to avoid clashes
with your existing workout names. The file is automatically saved, adding cz
before the file extension. If this would overwrite an existing file, the
smallest integer which provides a non-existing filename is added after cz, so
'original.tcx' might be saved to 'originalcz2.tcx' if originalcz.tcx and
originalcz1.tcx already existed.
