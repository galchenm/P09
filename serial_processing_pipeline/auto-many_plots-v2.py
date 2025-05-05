#!/usr/bin/env python3

"""
This script allows to plot in one figure two types of statistic files.
It is necessary to note, that before execution this script, you have to open Rsplit file and add one space before Rsplit column name.
Moreover, be careful with the order of files, because it is autumatically set color according their appearance:
if you want to have the same color for CC* plot and Rsplit plot files shoulde be placed at the same order:

CCstar1.dat CCstar2.dat CCstar3.dat ... Rsplit1.dat Rsplit2.dat Rsplit3.dat etc.
Additionally, the nubmer of colors is limited by ['b', 'g', 'r', 'c', 'm', 'y', 'k'], if you want more files,
please change the line: set_of_colours = ['b', 'g', 'r', 'c', 'm', 'y', 'k']

You are able to plot with adding limit to y-axis if you have a prior knowledge.

Example:
python3 many_plots.py -i p8snr5_CCstar.dat p8snr8_CCstar.dat -x '1/d centre' -y 'CC*' -s 100.0 -o tmp3.png -add_nargs p8snr5_Rsplit.dat p8snr8_Rsplit.dat -yad 'Rsplit/%'
"""
import os
import sys
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import numpy as np
from itertools import groupby, cycle 
from cycler import cycler
from collections import defaultdict

os.nice(0)

class CustomFormatter(argparse.RawDescriptionHelpFormatter,
                      argparse.ArgumentDefaultsHelpFormatter):
    pass


def parse_cmdline_args():
    parser = argparse.ArgumentParser(
        description=sys.modules[__name__].__doc__,
        formatter_class=CustomFormatter)

    parser.add_argument('-f', '--f', type=str, help="The file with lists of files with the same name of columns for their comparing")
    parser.add_argument('-i', '--i', nargs='+', type=str, help="List of files with the same name of columns for their comparing")
    
    parser.add_argument('-x', type=str, help="Name of x axis, for instance, '1/d centre'")
    parser.add_argument('-y', type=str, help="Name of y axis, for instance, CC*")
    parser.add_argument('-t','--t', type=str, help="Title")
    parser.add_argument('-legend', nargs='+', type=str, help="Legend")
    parser.add_argument('-s', '--scale', type=float, help="Scale koefficient for y-axis")

    parser.add_argument('-x_lim_up','--x_limit_up', type=float, help="Limit value for x axis")
    parser.add_argument('-x_lim_dw','--x_limit_dw', type=float, help="Limit value for x axis")

    parser.add_argument('-o','--o', type=str, help="Name of output path for saving pictures")

    parser.add_argument('-add_nargs', '--nargs_list_of_files', nargs='*', type=str, help="List of files for their comparing")
    parser.add_argument('-xad', '--x_add', type=str, help="Name of additional x axis, for instance, 1/d*, if you want to plot on the same picture")
    parser.add_argument('-yad', '--y_add', type=str, help="Name of additional y axis, for instance, CC*, if you want to plot on the same picture")

    parser.add_argument('-sad', '--scale_ad', type=float, help="Scale koefficient for y-axis")

    parser.add_argument('-l', '--logscale', default=False, action='store_true', help="Use log scale or not on y axis")
    parser.add_argument('-r', '--reverse', default=False, action='store_true', help="Use reverse x axis")
    parser.add_argument('-hor', '--horizontal',nargs='+', type=float, help="Value/s for horizontal line/s")
    parser.add_argument('-ver', '--vertical',nargs='+', type=float, help="Value/s for vertical line/s")
    parser.add_argument('-d', '--d', default=False, action='store_true', help="Use this flag if you want to show plot")
    
    return parser.parse_args()
  

def get_xy(file_name, x_arg_name, y_arg_name):
    x = []
    y = []

    with open(file_name, 'r') as stream:
        for line in stream:
            if y_arg_name in line:
                tmp = line.replace('1/nm', '').replace('# ', '').replace('centre', '').replace('/ A', '').replace(' dev','').replace('(A)','')
                tmp = tmp.split()
                y_index = tmp.index(y_arg_name)
                x_index = tmp.index(x_arg_name)

            else:
                tmp = line.split()
                x.append(float(tmp[x_index]))
                y.append(float(tmp[y_index]))

    
    x = np.array(x)
    y = np.array(y)
    
    list_of_tuples = list(zip(x, y))
    df = pd.DataFrame(list_of_tuples, 
                  columns = [x_arg_name, y_arg_name])
    
    df = df[df[y_arg_name].notna()]
    if y_arg_name is not 'CCano':
        df = df[df[y_arg_name] > 0.]
    
    return df[x_arg_name], df[y_arg_name]

def plot(d_input_files,  x_arg_name, y_arg_name, output, scale, x_add, y_add, scale_ad, legends, horizontal, vertical, logscale, reverse, x_limit_dw, x_limit_up, title, demonstrate, output_path):
    #x_arg_name = args.x
    #y_arg_name = args.y
    #output = args.o
    
    #print('x_arg_name, y_arg_name, output, scale, x_add, y_add, scale_ad, legends, horizontal, vertical, logscale, reverse, x_limit_dw, x_limit_up, y_limit_dw, y_limit_up, title, demonstrate')
    
    
    xxmin = 0.
    xxmax = -700000000000000000.
    
    yymin = 0.
    yymax = -700000000000000000.
    y_limit_down1 = 0
    y_limit_down2 = 0
    y_limit_up1 = -700000000000000000. 
    y_limit_up2 = -700000000000000000. 
    
    x_limit_down1 = 0
    x_limit_down2 = 0
    x_limit_up1 = -700000000000000000. 
    x_limit_up2 = -700000000000000000.
    
    input_files = d_input_files.keys()
    
    if len(input_files) >= 8:
        set_of_colours = [
        '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
        '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
        '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
        '#17becf', '#9edae5']  
    else:
        set_of_colours = ['b', 'g', 'r', 'c', 'm', 'y', 'k','o']
    
    colours_for_png = set_of_colours[:len(input_files)]
    current_path = os.getcwd()
    if output_path is None:
        path_to_plots = os.path.join(current_path, 'plots_res')
    else:
        path_to_plots = output_path

    if not os.path.exists(path_to_plots):
        os.mkdir(path_to_plots)
    
    f1, ax = plt.subplots()
    cy = cycler('color', colours_for_png)
    ax2 = ax.twinx() 
    ax.set_prop_cycle(cy)
    ax2.set_prop_cycle(cy)

    
    for file_name in input_files:
        x, y = get_xy(file_name, x_arg_name, y_arg_name)
        
        xxmax = max(x) if max(x) > xxmax else xxmax
        
        if '%' in y_arg_name:
            new_y_arg_name = y_arg_name.split('/')[0]
        else:
            new_y_arg_name = y_arg_name
        if scale is not None:
            y *= scale
            new_y_arg_name = f'{args.scale}x{new_y_arg_name}'
        yymax = max(y) if max(y) > yymax else yymax
        y_limit_down1 = min(y) if min(y) < y_limit_down1 else y_limit_down1
        y_limit_up1 = yymax     
        x_limit_down1 = min(x) if min(x) < x_limit_down1 else x_limit_down1
        x_limit_up1 = xxmax        
        ax.plot(x, y, marker='.', label="{}({}) of {}".format(new_y_arg_name, x_arg_name, file_name))
   

    if x_add is not None:
        compare_x_arg_name = x_add
    else:
        compare_x_arg_name = x_arg_name

    if y_add is not None:
        compare_y_arg_name = y_add
    else:
        compare_y_arg_name = y_arg_name
        
    new_compare_y_arg_name = None
    for ffile_name in input_files:
        if d_input_files[ffile_name] is not None:
            file_name = d_input_files[ffile_name]
            compare_x, compare_y = get_xy(file_name, compare_x_arg_name, compare_y_arg_name)
            
            xxmax = max(compare_x) if max(compare_x) > xxmax else xxmax
            
            if '%' in compare_y_arg_name:
                new_compare_y_arg_name = compare_y_arg_name.split('/')[0]
            else:
                new_compare_y_arg_name = compare_y_arg_name
            if scale_ad is not None:
                compare_y *= scale_ad
                new_compare_y_arg_name = f'{scale_ad}x{new_compare_y_arg_name}'
            yymax = max(compare_y) if max(compare_y) > yymax else yymax
            y_limit_down2 = min(y) if min(y) < y_limit_down2 else y_limit_down2
            y_limit_up2 = yymax
            x_limit_down2 = min(x) if min(x) < x_limit_down2 else x_limit_down2
            x_limit_up2 = xxmax             
            #ax.plot(compare_x, compare_y, marker='.', label="{}({}) of {}".format(new_compare_y_arg_name, compare_x_arg_name, file_name))
            ax2.plot(compare_x, compare_y, marker='.', label="{}({}) of {}".format(new_compare_y_arg_name, compare_x_arg_name, file_name))            
    
    if horizontal is not None:
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k','o'][:len(horizontal)]
        ver = 1.2
        for hor,c in zip(horizontal,colors):
            ax.axhline(y=hor, xmin=xxmin, xmax=xxmax, linestyle='--', label=f'y={hor}', c=c)
            ax.text(ver, hor, f'x={ver}', horizontalalignment='center', fontweight='bold', color='black')
            ver+=0.4
            
    if vertical is not None:
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k','o'][:len(args.vertical)]
        h = 15
        for ver,c in zip(vertical,colors):
            ax.axvline(x=ver, ymin=yymin, ymax=yymax, linestyle='--', label=f'x={ver}', c=c)
            ax.text(ver, h, f'x={ver}', rotation=90, verticalalignment='center', fontweight='bold', color='black')
            h+=10
    print('logscale' , logscale)
    if logscale:
        ax.set_yscale('log')
    
    nargs_list_of_files = np.array(d_input_files.values())
    nargs_list_of_files = np.where(nargs_list_of_files != None)[0]
    if new_compare_y_arg_name is not None:
        ax.set_ylabel(new_y_arg_name) # + ' / ' + new_compare_y_arg_name)
        ax2.set_ylabel(new_compare_y_arg_name)
    else:
        ax.set_ylabel(new_y_arg_name)
    '''
    if y_limit_dw is not None:
        y_limit_down = y_limit_dw
    else:
        y_limit_down = 0.
        
    if y_limit_up is not None:
        y_limit_up = y_limit_up
    else:
        y_limit_up = 100.    
    '''
    if x_limit_up is not None:
        x_limit_up = x_limit_up
    else:
        x_limit_up = 7.5

    if x_limit_dw is not None:
        x_limit_down = x_limit_dw
    else:
        x_limit_down = 0    
    
    
    y_limit_up1 = y_limit_up1 if y_limit_up1 <=100. else 100
    y_limit_up2 = y_limit_up2 if y_limit_up2 <=100. else 100

    y_limit_up1 = 1. if y_limit_up1 < 1. else y_limit_up1
    y_limit_up2 = 1. if y_limit_up2 < 1. else y_limit_up2

    x_limit_down1 = 1. if x_limit_down1 > 1. else x_limit_down
    x_limit_down2 = 1. if y_limit_up2 > 1. else x_limit_down
    
    x_limit_up1 = x_limit_up1 if x_limit_up1 < x_limit_up else x_limit_up
    x_limit_up2 = x_limit_up2 if x_limit_up2  < x_limit_up else x_limit_up
    
    #ax.set_ylim(y_limit_down1, y_limit_up1)
    #ax2.set_ylim(y_limit_down2, y_limit_up2)
    #print(y_limit_down1, y_limit_up1, y_limit_down2, y_limit_up2)
    ax.set(xlim = (x_limit_down, x_limit_up), ylim = (y_limit_down1, y_limit_up1), autoscale_on = True)
    ax2.set(xlim = (x_limit_down, x_limit_up), ylim = (y_limit_down2, y_limit_up2), autoscale_on = True)
    #ax.set_xlim(x_limit_down1 if x_limit_down1 < x_limit_down2 else x_limit_down2, x_limit_up1 if x_limit_up1 > x_limit_up2 else x_limit_up2)
    
    #ax.set(xlim = (x_limit_down1 if x_limit_down1 < x_limit_down2 else x_limit_down2, x_limit_up1 if x_limit_up1 > x_limit_up2 else x_limit_up2), ylim = (y_limit_down1, y_limit_up1), autoscale_on = True)
    #ax2.set(xlim = (x_limit_down1 if x_limit_down1 < x_limit_down2 else x_limit_down2, x_limit_up1 if x_limit_up1 > x_limit_up2 else x_limit_up2), ylim = (y_limit_down2, y_limit_up2), autoscale_on = True)
    if title is not None:
        ax.set_title(title)
    else:
        ax.set_title(output.split('.')[0])
    if reverse:
        ax.invert_xaxis()
    
    ax.legend(legends, loc="center left")
    
    if x_arg_name == '1/d':
        ax.set_xlabel(x_arg_name + ' 1/nm')
    elif x_arg_name == 'd':
        ax.set_xlabel(x_arg_name + ' A')
    else:
        ax.set_xlabel(x_arg_name)
    
    if len(output) > 0 and output is not None:
        f1.savefig(output)
        print(os.path.dirname(os.path.abspath(output)),  os.path.dirname(os.path.abspath(output))!= path_to_plots)
        if os.path.dirname(os.path.abspath(output))!= path_to_plots:
            shutil.move(output, path_to_plots)
    
    if demonstrate:
        plt.show()

if __name__ == "__main__":
    args = parse_cmdline_args()
    total_input_files = defaultdict(dict)
    
    if args.f is None:
        input_files = args.i
    else:
        with open(args.f,'r') as file:
            
            for line in file:
                line = line.strip()
                first, second = line.split(':') if ':' in line else [line, None]
                
                if first.isdigit():
                    
                    key_value = first
                    output_filename = second
                    
                else:
                    total_input_files[output_filename][first] = second 
    
    
    for i in total_input_files.keys():
        d_input_files = total_input_files[i]
        plot(d_input_files,  args.x, args.y, i, args.scale, args.x_add, args.y_add, args.scale_ad, args.legend, args.horizontal, args.vertical, args.logscale, args.reverse, args.x_limit_dw, args.x_limit_up, args.t, args.d, args.o)
    