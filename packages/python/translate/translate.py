import tkinter
from tkinter import _tkinter
from tkinter import Tcl
from typing import Dict, Any, Union, List, Optional, Tuple
import yaml
import os
import re

def tcl_value2python_value(value: Union[str, tuple]) -> Union[str, List[Any]]:
    """
    将输入值转换为列表或字符串
    Args:
        value: 输入值，可以是字符串或元组
    Returns:
        如果输入是元组，转换为列表（包括处理嵌套元组）
        如果输入是字符串：
            - 如果包含大括号，解析为列表
            - 否则返回原始字符串
    Examples:
        ("a", "b", ("c", "d")) -> ["a", "b", ["c", "d"]]
        "a b {c d} e" -> ["a", "b", ["c", "d"], "e"]
        "{a b}" -> ["a", "b"]
        "simple string" -> "simple string"
    """
    # 处理元组输入
    if isinstance(value, tuple):
        return [tcl_value2python_value(item) if isinstance(item, (str, tuple)) else item for item in value]
    
    # 确保value是字符串类型
    if not isinstance(value, str):
        return value
    
    # 去除首尾空格
    value = value.strip()
    
    # 如果是空字符串，直接返回
    if not value:
        return ""
    
    # 如果没有大括号，直接返回字符串
    if '{' not in value and '}' not in value:
        return value
    
    def parse_list(s: str, start: int) -> Tuple[List[Any], int]:
        """递归解析大括号内的内容"""
        result = []
        current = []
        i = start
        
        while i < len(s):
            if s[i] == '{':
                # 递归处理嵌套的大括号
                nested_list, new_i = parse_list(s, i + 1)
                if current:
                    result.append(''.join(current).strip())
                    current = []
                result.append(nested_list)
                i = new_i
            elif s[i] == '}':
                # 处理当前积累的字符
                if current:
                    result.append(''.join(current).strip())
                return result, i + 1
            elif s[i] == ' ' and current:
                # 空格分隔的词
                result.append(''.join(current).strip())
                current = []
            else:
                current.append(s[i])
            i += 1
        
        # 处理最后一个词
        if current:
            result.append(''.join(current).strip())
        return result, i
    
    # 如果整个值被大括号包围，去掉外层大括号并解析
    if value.startswith('{') and value.endswith('}'):
        result, _ = parse_list(value, 1)
        return result
    
    # 其他情况，从当前位置开始解析
    result, _ = parse_list(value, 0)
    return result

def python_value2tcl_value(value: Union[str, List[Any]]) -> str:
    """
    将Python值转换为TCL格式的字符串
    Args:
        value: Python值，可以是字符串或列表
    Returns:
        TCL格式的字符串
    Example:
        [1, 2, [3, 4]] -> "[list 1 2 [list 3 4]]"
        "a b {c d} e" -> "[list a b [list c d] e]"
        [1, "a b", [2, 3]] -> "[list 1 {a b} [list 2 3]]"
        "" -> '""'
        [] -> '""'
    """
    # 处理空值情况
    if value == "" or value is None:
        return '""'
    elif isinstance(value, list) and not value:
        return '""'
    
    if isinstance(value, list):
        # 处理列表：递归转换每个元素
        elements = []
        for item in value:
            if isinstance(item, list):
                # 递归处理嵌套列表
                elements.append(python_value2tcl_value(item))
            elif isinstance(item, str) and (' ' in item or '{' in item or '}' in item):
                # 如果字符串包含空格或大括号，用大括号包围
                elements.append('{' + item + '}')
            elif item == "" or item is None:
                # 处理列表中的空值
                elements.append('""')
            else:
                # 其他情况直接转换为字符串
                elements.append(str(item))
        return f"[list {' '.join(elements)}]"
    
    elif isinstance(value, str):
        if '{' in value or '}' in value:
            # 处理包含大括号的字符串
            parts = []
            current = ''
            brace_level = 0
            
            for char in value:
                if char == '{':
                    if brace_level == 0 and current:
                        # 开始新的大括号组之前，处理之前的部分
                        parts.extend(current.strip().split())
                        current = ''
                    brace_level += 1
                elif char == '}':
                    brace_level -= 1
                    if brace_level == 0:
                        # 大括号组结束，递归处理大括号内的内容
                        inner_content = current.strip()
                        if inner_content:
                            parts.append(f"[list {' '.join(inner_content.split())}]")
                        current = ''
                        continue
                current += char
                
            if current.strip():
                # 处理剩余部分
                parts.extend(current.strip().split())
                
            return f"[list {' '.join(parts)}]"
        
        elif ' ' in value:
            # 处理包含空格的普通字符串
            return f"[list {value}]"
        
        else:
            # 处理普通字符串
            return value
    
    else:
        # 处理其他类型（数字等）
        return str(value)

def set_nested_dict(d: Dict[str, Any], keys: List[str], value: Any) -> None:
    """
    在嵌套字典中设置值
    Args:
        d: 目标字典
        keys: 键的列表，表示嵌套路径
        value: 要设置的值
    Example:
        d = {}
        set_nested_dict(d, ['a', 'b', 'c'], 1)
        # 结果: {'a': {'b': {'c': 1}}}
    """
    current = d
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = value

def tcl_to_dict(file_path: str) -> Dict[str, Any]:
    """
    将TCL文件转换为Python字典
    Args:
        file_path: TCL文件路径
    Returns:
        转换后的字典
    Example:
        # 输入TCL文件内容:
        # set var 1
        # set a(b,c,d) 2
        # set arr(x) {1 2 3}
        # 
        # 输出字典:
        # {
        #     'var': 1,
        #     'a': {'b': {'c': {'d': 2}}},
        #     'arr': {'x': [1, 2, 3]}
        # }
    """
    # 创建TCL解释器
    tcl = Tcl()
    
    # 获取初始变量列表（内置变量）
    builtin_vars = set(tcl.eval('info vars').split())
    
    # 加载TCL文件
    file_path = os.path.abspath(file_path).replace('\\', '/')
    tcl.eval(f'source "{file_path}"')
    
    # 获取所有用户定义的变量（排除内置变量）
    user_vars = set(tcl.eval('info vars').split()) - builtin_vars
    
    result = {}
    
    # 处理每个变量
    for var in user_vars:
        try:
            # 检查变量是否是数组
            is_array = tcl.eval(f'array exists {var}') == '1'
            
            if is_array:
                # 获取数组所有的键
                array_keys = tcl.eval(f'array names {var}').split()
                
                # 处理每个数组元素
                for key in array_keys:
                    # 获取值并转换
                    #value = tcl.getvar(f'{var}({key})')
                    value = str(tcl.eval(f'set {var}({key})'))
                    value = tcl_value2python_value(value)
                    
                    # 处理键路径（将逗号分隔的键转换为嵌套路径）
                    key_parts = [k.strip() for k in key.split(',')]
                    
                    # 确保变量存在于结果字典中
                    if var not in result:
                        result[var] = {}
                    
                    # 设置嵌套值
                    set_nested_dict(result[var], key_parts, value)
            else:
                # 处理普通变量
                try:
                    #value = tcl.getvar(f'{var}')
                    value = str(tcl.eval(f'set {var}'))
                    result[var] = tcl_value2python_value(value)
                except _tkinter.TclError:
                    continue
                    
        except Exception as e:
            print(f"Error processing variable {var}: {str(e)}")
            continue
    
    return result

def yaml_to_dict(yaml_file: str) -> Dict[str, Any]:
    """
    从YAML文件读取数据到字典
    Args:
        yaml_file: YAML文件路径
    Returns:
        包含YAML数据的字典
    """
    with open(yaml_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def dict_to_tcl(data: Union[Dict[str, Any], Dict[str, Dict[str, Any]]], tcl_file: str, with_source: bool = False) -> None:
    """
    将字典写入TCL文件
    Args:
        data: 字典数据。如果with_source为True，则key为来源名称，value为配置字典
        tcl_file: 输出文件路径
        with_source: 是否包含来源信息
    """
    def process_dict(d: Dict[str, Any], prefix: str = '') -> List[str]:
        lines = []
        for key, value in d.items():
            if isinstance(value, dict):
                # 递归处理嵌套字典
                lines.extend(process_dict(value, f'{prefix},{key}' if prefix else key))
            else:
                # 处理基本类型
                var_name = f'{prefix},{key}' if prefix else key
                # 如果变量名包含逗号，转换为TCL数组格式
                if ',' in var_name:
                    parts = var_name.split(',')
                    var_name = f'{parts[0]}({",".join(parts[1:])})'
                value = python_value2tcl_value(value)
                lines.append(f'set {var_name} {value}')
        return sorted(lines)

    try:
        with open(tcl_file, 'w', encoding='utf-8') as f:
            if with_source:
                # 写入文件头部注释
                f.write("# 合并的配置\n")
                f.write("# 包含以下来源：\n")
                for source_name in data.keys():
                    f.write(f"# - {source_name}\n")
                f.write("\n")
                
                # 按来源分组写入配置
                for source_name, source_dict in data.items():
                    f.write(f"\n# ===== 来源: {source_name} =====\n")
                    tcl_lines = process_dict(source_dict)
                    f.write('\n'.join(tcl_lines) + '\n')
            else:
                # 直接写入配置
                tcl_lines = process_dict(data)
                f.write('\n'.join(tcl_lines) + '\n')
    except Exception as e:
        print(f"写入TCL文件时出错: {str(e)}")
        raise

def dict_to_yaml(data: Dict[str, Any], output_file: str) -> None:
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=True, default_flow_style=False)
    except Exception as e:
        print(f"写入YAML文件时出错: {str(e)}")
        raise

def dict_to_tcl_with_source(data: Dict[str, Dict[str, Any]], output_file: str) -> None:
    """
    将字典写入TCL文件，包含来源信息
    Args:
        data: 带来源信息的字典，key为来源名称，value为配置字典
        output_file: 输出文件路径
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入文件头部注释
            f.write("# 合并的配置\n")
            f.write("# 包含以下来源：\n")
            for source_name in data.keys():
                f.write(f"# - {source_name}\n")
            f.write("\n")
            
            # 按来源分组写入配置
            for source_name, source_dict in data.items():
                f.write(f"\n# ===== 来源: {source_name} =====\n")
                # 使用dict_to_tcl的核心逻辑，但直接写入文件
                def process_dict(d: Dict[str, Any], prefix: str = '') -> List[str]:
                    lines = []
                    for key, value in d.items():
                        if isinstance(value, dict):
                            # 递归处理嵌套字典
                            lines.extend(process_dict(value, f'{prefix},{key}' if prefix else key))
                        else:
                            # 处理基本类型
                            var_name = f'{prefix},{key}' if prefix else key
                            # 如果变量名包含逗号，转换为TCL数组格式
                            if ',' in var_name:
                                parts = var_name.split(',')
                                var_name = f'{parts[0]}({",".join(parts[1:])})'
                            value = python_value2tcl_value(value)
                            lines.append(f'set {var_name} {value}')
                    return lines
                
                tcl_lines = process_dict(source_dict)
                f.write('\n'.join(tcl_lines) + '\n')
                
    except Exception as e:
        print(f"写入TCL文件时出错: {str(e)}")
        raise

def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], overwrite: bool = True) -> Dict[str, Any]:
    """
    合并两个字典，支持嵌套字典的合并
    Args:
        dict1: 第一个字典
        dict2: 第二个字典
        overwrite: 当键冲突时，是否用dict2的值覆盖dict1的值
    Returns:
        合并后的字典
    Example:
        d1 = {'a': 1, 'b': {'c': 2}}
        d2 = {'b': {'d': 3}, 'e': 4}
        merged = merge_dicts(d1, d2)
        # 结果: {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 如果两个值都是字典，递归合并
            result[key] = merge_dicts(result[key], value, overwrite)
        elif key not in result or overwrite:
            # 如果键不存在或允许覆盖，则更新值
            result[key] = value
            
    return result

def process_config_inputs(inputs: List[Union[str, Dict[str, Any]]], output_file: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """
    处理配置输入，支持混合输入（文件路径和字典）
    Args:
        inputs: 配置输入列表，每个元素可以是：
               - TCL文件路径
               - YAML文件路径
               - 配置字典
        output_file: 输出文件路径，可选。根据扩展名决定输出格式
    Returns:
        Tuple[合并后的字典, 各来源的字典]
    Example:
        inputs = [
            'd:/config1.tcl',          # TCL文件
            'd:/config2.yaml',         # YAML文件
            {'var1': 'value1'},        # 字典1
            {'var2': 'value2'}         # 字典2
        ]
        merged, individual = process_config_inputs(inputs, 'output.tcl')
    """
    # 存储每个来源的字典
    source_dicts = {}
    merged_dict = {}
    
    # 处理每个输入
    for i, input_item in enumerate(inputs):
        try:
            if isinstance(input_item, dict):
                # 处理字典输入
                current_dict = input_item
                source_name = f"Appendix info apply"
                if i == 0:
                    source_name = "Basic Appendix info"
                if i == len(inputs) - 1:
                    source_name = "Fixed Appendix info"
            elif isinstance(input_item, str):
                # 处理文件输入
                ext = os.path.splitext(input_item)[1].lower()
                if ext == '.tcl':
                    current_dict = tcl_to_dict(input_item)
                    source_name = input_item
                elif ext == '.yaml' or ext == '.yml':
                    current_dict = yaml_to_dict(input_item)
                    source_name = input_item
                else:
                    print(f"警告: 不支持的文件类型 {input_item}")
                    continue
            else:
                print(f"警告: 不支持的输入类型 {type(input_item)}")
                continue
            
            # 存储当前来源的字典
            source_dicts[source_name] = current_dict
            
            # 合并到主字典
            merged_dict = merge_dicts(merged_dict, current_dict) if merged_dict else current_dict.copy()
            
        except Exception as e:
            print(f"处理输入 {input_item} 时出错: {str(e)}")
            continue
    
    # 如果指定了输出文件，则写入结果
    if output_file:
        try:
            ext = os.path.splitext(output_file)[1].lower()
            if ext == '.tcl':
                dict_to_tcl(source_dicts, output_file, with_source=True)
            elif ext == '.yaml' or ext == '.yml':
                dict_to_yaml(merged_dict, output_file)
            else:
                print(f"警告: 不支持的输出文件类型 {output_file}")
        except Exception as e:
            print(f"写入输出文件时出错: {str(e)}")
    
    return merged_dict, source_dicts

if __name__ == '__main__':
    inputs = [
        {'var1': 'value1', "var2": "value2"},           # 字典1
        'd:/edp/try_run/t1.tcl',      # TCL文件
        'd:/edp/try_run/t1.yaml',     # YAML文件
        {'var2': 'value2'}            # 字典2
    ]
    merged, individual = process_config_inputs(inputs, 'd:/edp/try_run/merged.tcl')
    merged, individual = process_config_inputs(inputs, 'd:/edp/try_run/merged.yaml')