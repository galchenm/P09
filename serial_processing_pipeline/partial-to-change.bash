#!/bin/bash

INPUT=$1
stream=$(sed 's/.stream//g'<<<$(basename $INPUT))

data=${stream}_partial
pg=$2 #"mmm" 
pdb=$3 #"/gpfs/exfel/u/scratch/SPB/202122/p002934/galchenm/pdb/pha.cell"

HIGHRES=$4 #1.8
resext=0.0 # total CC* is calculated to highres+resext
highres="--highres=${HIGHRES}"      #<- number gives res limit
nsh=20 # number of shells
#maxB="--max-rel-B=50"
model=xsphere
#model=unity
iterations=3 #2,3
push="--push-res=1.0" #"--push-res=0.2" "--push-res=0.5" "--push-res=1.5"
minres="--min-res=5"

partialator="partialator"

ERRORDIR=error

source /etc/profile.d/modules.sh
module load xray
module load hdf5/1.10.5
module load anaconda3/5.2
module load maxwell crystfel
    # Job name
    NAME=$data

    SLURMFILE="${NAME}.sh"

    echo "#!/bin/sh" > $SLURMFILE
    echo >> $SLURMFILE

#    echo "#SBATCH --partition=cfel" >> $SLURMFILE  # Set your partition here
    echo "#SBATCH --partition=upex" >> $SLURMFILE  # Set your partition here

    echo "#SBATCH --time=12:00:00" >> $SLURMFILE
#    echo "#SBATCH --exclude=max-exfl109,max-exfl103" >> $SLURMFILE
    echo "#SBATCH --nodes=1" >> $SLURMFILE
    echo "#SBATCH --nice=100" >> $SLURMFILE
    echo "#SBATCH --mem=500000" >> $SLURMFILE
    echo "#SBATCH --cpu-freq=2600000" >> $SLURMFILE  # TO TEST !!!
    echo >> $SLURMFILE

#    echo "#SBATCH --workdir   $PWD" >> $SLURMFILE
    echo "#SBATCH --job-name  $NAME" >> $SLURMFILE
    echo "#SBATCH --output    $ERRORDIR/$NAME-%N-%j.out" >> $SLURMFILE
    echo "#SBATCH --error     $ERRORDIR/$NAME-%N-%j.err" >> $SLURMFILE
    echo >> $SLURMFILE

    echo "source /etc/profile.d/modules.sh" >> $SLURMFILE
    echo "module load xray" >> $SLURMFILE
    echo "module load hdf5/1.10.5">> $SLURMFILE
	echo "module load anaconda3/5.2">> $SLURMFILE
	echo "module load maxwell crystfel">> $SLURMFILE
	echo "export QT_QPA_PLATFORM=offscreen" >> $SLURMFILE 
    
    echo >> $SLURMFILE

	command="$partialator --no-logs --iterations=$iterations --model=$model "$minres" "$push" -i $stream.stream -o $data.hkl -y $pg -j 80"
    echo $command >> $SLURMFILE
        #total CC* calculation
    highres1="--highres="`echo $HIGHRES + $resext | bc`
#    echo $highres1
    command="compare_hkl -p $pdb -y $pg $highres1 --nshells=1 --fom=CCstar --shell-file=${data}_CCstarTotal.dat $data.hkl1 $data.hkl2"
    echo $command >> $SLURMFILE

    command="compare_hkl -p $pdb -y $pg $highres --nshells=$nsh --fom=CCstar --shell-file=${data}_CCstar.dat $data.hkl1 $data.hkl2"
    echo $command >> $SLURMFILE

    command="compare_hkl -p $pdb -y $pg "$highres" --nshells=$nsh --fom=Rsplit --shell-file=${data}_Rsplit.dat $data.hkl1 $data.hkl2"
    echo $command >> $SLURMFILE

    command="compare_hkl -p $pdb -y $pg "$highres" --nshells=$nsh --fom=CC --shell-file=${data}_CC.dat $data.hkl1 $data.hkl2"
    echo $command >> $SLURMFILE

    command="compare_hkl -p $pdb -y $pg "$highres" --nshells=$nsh --fom=CCano --shell-file=${data}_CCano.dat $data.hkl1 $data.hkl2"
    echo $command >> $SLURMFILE

    command="check_hkl -p $pdb -y $pg "$highres" --nshells=$nsh --shell-file=${data}_SNR.dat $data.hkl"
    echo $command >> $SLURMFILE

    command="check_hkl -p $pdb -y $pg "$highres" --nshells=$nsh --wilson --shell-file=${data}_Wilson.dat $data.hkl"
    echo $command >> $SLURMFILE
	
	max_dd=$(echo "scale=3;10./${HIGHRES}" | bc)

	command="python3 many_plots-upt-v2.py -i ${data}_CCstar.dat -x '1/d' -y 'CC*' -o ${data}.png -add_nargs ${data}_Rsplit.dat -yad 'Rsplit/%' -x_lim_dw 1. -x_lim_up ${max_dd} -t ${data} -legend ${data} >> $ERRORDIR/output.err"
	echo $command >> $SLURMFILE
	
	
	command="python3 avr-peakogram-stream -i $stream.stream"
	echo $command >> $SLURMFILE
	
	
	command="python3 orientation-v2.py $stream.stream"
	echo $command >> $SLURMFILE
	
    sbatch $SLURMFILE