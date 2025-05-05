These two scripts can help to visualize such statistics as CC*, Rsplit and etc. versus 1/d, where d is a resolution [A]

Below you can see their usage:

python3 many_plots-upt-v2.py -i 1_CCstar.dat 2_CCstar.dat -x '1/d' -y 'CC*' -o [name of your plot with the extension] -add_nargs 1_Rsplit.dat 2_Rsplit.dat -yad 'Rsplit/%' -x_lim_dw number1 -x_lim_up number2 -t [put title] -legend [put the legend here]  [--d, use this option if you want to show plots]

You can add here as many files as you need.
The result of this script will be [name of your plot with the extension] plot with CC* and Rsplit statistics for 1_ and 2_d datasets.

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

python3 auto-many_plots-v2.py -f  list_of_files.lst -x '1/d' -y 'CCano' -o /path_where_to_save_plot -x_lim_dw number1 -x_lim_up number2 -legend [put the legend here] 

where list_of_files.lst should have the following structure:

1:2p5res_step_25eV_width_100eV_CCano.svg
abspath_to_1_CCano.dat
...
abspath_to_N_CCano.dat

If you want to plot, for instance, CC* and Rsplit on the same figure but separeately for each datasets, you can follow the following example:

python3 auto-many_plots-v2.py -f CCstar-Rsplit.lst -x '1/d' -y 'CC*' -o /path_where_to_save_plot -yad 'Rsplit/%' -x_lim_dw number1 -x_lim_up number2 -legend [your legend] [--d, use this option if you want to show plots]

where CCstar-Rsplit.lst looks like this:

1:name_of_the_plot1.png
1_CCstar.dat:1_Rsplit.dat
2_CCstar.dat:2_Rsplit.dat
...
K:name_of_the_plotK.png
3_CCstar.dat:3_Rsplit.dat
4_CCstar.dat:4_Rsplit.dat

The result of running this script with CCstar-Rsplit.lst will be two plots (name_of_the_plot1.png, name_of_the_plot2.png), where on name_of_the_plot1.png you can see statistics from 1_ and 2_ datasets, etc.

If you have any recomendations/suggestions, do not hesitate to contact me!
