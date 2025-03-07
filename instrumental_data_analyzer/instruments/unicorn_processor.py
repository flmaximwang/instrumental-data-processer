import os
import re
from typing import Mapping
import pandas as pd
from instrumental_data_analyzer.abstracts.signal_1d import ContinuousSignal1D, DiscreteSignal1D, FractionSignal, Signal1D
from instrumental_data_analyzer.abstracts.signal_1d_collection import Signal1DCollection
from instrumental_data_analyzer.utils import path_utils
from ..concretes.chrom import *

def extract_number_from_chrom(chrom_string):
    '''
    从chromatogram的字符串中提取编号
    '''
    my_pattern = re.compile(r'Chrom\.(\d+)')
    my_match = my_pattern.match(chrom_string)
    
    if my_match:
        return int(my_match.group(1)) - 1
    else:
        return None

class UnicChrom(Chrom):
    
    @staticmethod
    def from_exported_file(file_path, name=None):
        raw_data = pd.read_csv(file_path, sep='\t', encoding='UTF-16 LE', header=None, na_values='') # 空字符串不识别为 NaN
        chrom_series_name = path_utils.get_name_from_path(file_path)
        # 第一行显示 chromatogram 的编号, 第二行显示信号的类型, 第三行为交替的时间和信号值
        results: Mapping[int, list] = {}
        for n, chrom_string in enumerate(raw_data.iloc[0, 0::2]):
            chrom_number = extract_number_from_chrom(chrom_string)
            if not chrom_number in results.keys():
                results[chrom_number] = []
                results[chrom_number].append(n)
            else:
                results[chrom_number].append(n)
        chromatograms: list[Chrom] = []
        signals: list[ChromSig, ChromLog]
        for i in results.keys():
            signals = []
            for n in results[i]:
                signal_data = raw_data.iloc[3:, 2*n:2*n+2].copy()
                signal_name = raw_data.iloc[1, 2*n]
                if any([re.match(pattern, signal_name) for pattern in ["UV", "UV \d_\d{3}", "Cond", "Conc B", "UV_CUT_TEMP@100,BASEM", "pH", "PreC pressure", "DeltaC pressure", "PostC pressure", "System pressure"]]):
                    # 设置 signal_data 的 2 列为 float
                    signal_data = signal_data.astype(float).dropna() 
                    signals.append(
                        ChromSig(
                            data=signal_data,
                            name=signal_name,
                            axis_name="Volume",
                            axis_unit="ml",
                            value_name=signal_name,
                            value_unit=raw_data.iloc[2, 2*n+1]
                        )
                    )
                elif raw_data.iloc[1, 2*n] in ["Injection", "Fraction", "Run Log"]:
                    # 设置 signal_data 的 2 列为 float 和 str
                    signal_data = signal_data.astype({signal_data.columns[0]: float, signal_data.columns[1]: str}).dropna()
                    signals.append(
                        ChromLog(
                            data=signal_data,
                            name=signal_name,
                            axis_name="Volume",
                            axis_unit="ml",
                            value_name=signal_name,
                            value_unit=None
                        )
                    )
                else:
                    raise Exception(f"Unknown signal type: {raw_data.iloc[1, 2*n]}")
            chromatograms.append(Chrom(signals, name=f"{chrom_series_name}_{i}"))
        for chrom in chromatograms:
            axis_min, axis_max = None, None
            for sig_name in chrom:
                axis_min = min(chrom[sig_name].get_axis()) if not axis_min or min(chrom[sig_name].get_axis()) < axis_min else axis_min
                axis_max = max(chrom[sig_name].get_axis()) if not axis_max or max(chrom[sig_name].get_axis()) > axis_max else axis_max
            chrom.set_axis_limit((axis_min, axis_max))
        
        return chromatograms