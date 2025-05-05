; Manually optimized with hdfsee
; Manually optimized with hdfsee
clen = 0.2214 ;$DETECTOR_DISTANCE ;0.220995 ;$DETECTOR_DISTANCE ;0.1 
photon_energy = $PHOTON_ENERGY 

;photon_energy = 16000
adu_per_photon = 1
;clen = 0.4013 ; from XDS
;clen = 0.2116
;clen = /LCLS/detectorPosition
;coffset = 0.0
res = 5814.0  ; 172 micron pixel size

rigid_group_d0 = 0
rigid_group_collection_quadrants = d0
rigid_group_collection_asics = d0


flag_lessthan = 0

;bad_beamstop/min_x = -50
;bad_beamstop/max_x = 50
;bad_beamstop/min_y = -100
;bad_beamstop/max_y = 2000

0/min_fs = 0
0/max_fs = 2462
0/min_ss = 0
0/max_ss = 2526
0/corner_x = $ORGX ;-1254.480840
0/corner_y = $ORGY ;-1157.864072
0/fs = +1.000000x +0.000000y
0/ss = +0.000000x +1.000000y

