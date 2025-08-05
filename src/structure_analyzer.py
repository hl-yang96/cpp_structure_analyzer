#/usr/bin/python
from pygccxml import parser, declarations, utils
import time
import traceback
import logging
import json
from enum import Enum
import argparse
# from funcy import log_durations

class CppStructClassAnalyzer:
    '''
    RepoAnalyzer is used to analyze the cpp struct or class
    and generate the type tree
    '''

    FUNDAMENTAL_LIST = [
        # Void type
        "void",

        # Boolean type
        "bool",

        # Character types
        "char",
        "signed char",
        "unsigned char",
        "wchar_t",
        "char16_t",
        "char32_t",
        "char8_t",  # C++20

        # Integer types - signed
        "int",
        "signed int",
        "short",
        "short int",
        "signed short",
        "signed short int",
        "long",
        "long int",
        "signed long",
        "signed long int",
        "long long",
        "long long int",
        "signed long long",
        "signed long long int",

        # Integer types - unsigned
        "unsigned",
        "unsigned int",
        "unsigned short",
        "unsigned short int",
        "unsigned long",
        "unsigned long int",
        "unsigned long long",
        "unsigned long long int",

        # Fixed-width integer types (C++11)
        "int8_t",
        "int16_t",
        "int32_t",
        "int64_t",
        "uint8_t",
        "uint16_t",
        "uint32_t",
        "uint64_t",
        "intptr_t",
        "uintptr_t",
        "intmax_t",
        "uintmax_t",

        # Fast and least integer types
        "int_fast8_t",
        "int_fast16_t",
        "int_fast32_t",
        "int_fast64_t",
        "uint_fast8_t",
        "uint_fast16_t",
        "uint_fast32_t",
        "uint_fast64_t",
        "int_least8_t",
        "int_least16_t",
        "int_least32_t",
        "int_least64_t",
        "uint_least8_t",
        "uint_least16_t",
        "uint_least32_t",
        "uint_least64_t",

        # Floating-point types
        "float",
        "double",
        "long double",

        # Common typedefs
        "size_t",
        "ssize_t",
        "ptrdiff_t",
        "nullptr_t",  # C++11

        # Platform-specific types (common ones)
        "time_t",
        "clock_t",
        "off_t",
        "pid_t",
        "uid_t",
        "gid_t",
    ]

    VALUE_CONTAINERS = [
        # 序列容器（顺序存储，支持随机或顺序访问）
        "std::vector",          # 动态数组，支持随机访问
        "std::deque",           # 双端队列，两端插入删除高效
        "std::list",            # 双向链表，任意位置插入删除高效
        "std::forward_list",    # 单向链表，内存占用更小
        "std::array",           # 固定大小数组，std::array<T, N>

        # 关联容器（自动排序，基于值的唯一性）
        "std::set",             # 有序集合，元素唯一
        "std::multiset",        # 有序多重集合，允许重复元素
        "std::unordered_set",   # 无序集合（哈希表），元素唯一
        "std::unordered_multiset", # 无序多重集合，允许重复元素

        # 容器适配器（基于其他容器实现的特殊接口）
        "std::stack",           # 栈（LIFO），默认基于deque实现
        "std::queue",           # 队列（FIFO），默认基于deque实现
        "std::priority_queue",  # 优先队列（堆），默认基于vector实现

        # 第三方高性能容器库
        "tsl::sparse_set",      # 稀疏集合，内存效率高
        "tsl::robin_set",       # Robin Hood哈希集合
        "tsl::hopscotch_set",   # Hopscotch哈希集合
        "boost::container::vector",  # Boost版本的vector
        "boost::container::list",    # Boost版本的list
        "boost::container::set",     # Boost版本的set
        "absl::flat_hash_set",       # Abseil扁平哈希集合
        "absl::node_hash_set",       # Abseil节点哈希集合

        # you can add more third-party value containers here
    ]
    
    KV_CONTAINERS = [
        """
        键值对容器列表 - 有两个主要模板参数（键类型和值类型）的容器

        特点：
        1. 这些容器有两个主要模板参数：Key 和 Value
        2. 分析时需要递归分析两个类型参数
        3. 例如：std::map<std::string, UserInfo> 需要分析 string 和 UserInfo

        用途：
        - 在 analyze_string_container() 中用于识别键值对容器
        - 分别分析键类型和值类型
        - 在JSON输出中区分 container_k_type 和 container_v_type
        """

        # 配对类型（最基础的键值对结构）
        "std::pair",            # 二元组，std::pair<Key, Value>
        "std::tuple",           # 多元组，可以有多个类型参数

        # 关联容器（键值映射，自动按键排序）
        "std::map",             # 有序映射，键唯一，基于红黑树
        "std::multimap",        # 有序多重映射，键可重复
        "std::unordered_map",   # 无序映射（哈希表），键唯一
        "std::unordered_multimap", # 无序多重映射，键可重复

        # 第三方高性能键值对容器
        "tsl::sparse_map",      # 稀疏映射，内存效率高
        "tsl::robin_map",       # Robin Hood哈希映射
        "tsl::hopscotch_map",   # Hopscotch哈希映射
        "boost::container::map",     # Boost版本的map
        "boost::container::multimap", # Boost版本的multimap
        "boost::unordered_map",      # Boost版本的unordered_map
        "boost::unordered_multimap", # Boost版本的unordered_multimap
        "absl::flat_hash_map",       # Abseil扁平哈希映射
        "absl::node_hash_map",       # Abseil节点哈希映射
        "absl::btree_map",           # Abseil B树映射

        # you can add more third-party key-value containers here
    ]

    class TypeDetailCache:
        """
        类型详情缓存类

        作用：
        1. 缓存已经分析过的类型信息，避免重复分析提高性能
        2. 处理类型名称的标准化（去除前导::）
        3. 提供缓存的增删查改操作
        4. 支持将缓存信息保存到文件

        使用场景：
        - 当分析复杂的嵌套结构时，同一个类型可能被多次引用，例如： std::vector<UserInfo> 和 std::map<int, UserInfo> 都包含 UserInfo
        - 缓存可以避免对 UserInfo 进行重复的递归分析
        """

        def __init__(self):
            """初始化缓存字典"""
            self.type_detail_cache_ = {}  # 存储类型名 -> 分析结果的映射

        def add_type_cache(self, k, v):
            """
            添加类型缓存
            Args:
                k (str): 类型名称（键）
                v (dict): 类型分析结果（值）
            功能：
                - 标准化类型名称（去除前导::）
                - 将分析结果存入缓存
            示例：
                add_type_cache("::UserInfo", {...})
                实际存储为 "UserInfo" -> {...}
            """
            if k == None or len(k) == 0:
                return
            # 标准化类型名：去除前导的"::"，因为 "::Asset" 和 "Asset" 是同一个类型
            _k = k[2 if k[0 : 2] == "::" else 0:]
            self.type_detail_cache_[_k] = v

        def get_type_cache(self, k):
            """
            获取类型缓存
            Args:
                k (str): 类型名称
            Returns:
                dict: 类型分析结果，如果未找到返回 None
            功能：
                - 标准化类型名称后查找缓存
                - 提高重复类型分析的性能
            """
            if k == None or len(k) == 0:
                return None
            # 同样进行类型名标准化
            _k = k[2 if k[0 : 2] == "::" else 0 : ]
            res = self.type_detail_cache_.get(_k, None)
            return res

        def remove_type_cache(self, k):
            """移除类型缓存，注意：这里直接使用原始键名，没有进行标准化处理，可能需要根据实际使用情况调整
            """
            _ = self.type_detail_cache_.pop(k, None)

        def save_cache_info(self, output=None):
            """保存数据信息到文件，作为所有依赖的类型分析结果
            """
            if output != None:
                with open(output, "w") as w:
                    json.dump(self.type_detail_cache_, w, indent=4, sort_keys=True)
    
    def __init__(self, only_public_var=True ,file_path_black_list=[]):
        '''
        @file: the file needed to be analyzed, default `None`
        @cflags: shell flags for clang++, default `None`
        @only_public_var: default `True`, will only analyze the public variables of a class/struct
        @file_path_black_list: default `[]`, the class which is declaration under the paths will be ignore
        '''
        self.only_public_var_ = only_public_var
        self.filepath_black_list_ = file_path_black_list
        self.cache_ = CppStructClassAnalyzer.TypeDetailCache()
        self.global_ns_ = None
        self.find_class_cost = 0
        self.not_find_class_cost = 0
        self.find_typedef_cost = 0
        self.find_enum_cost = 0
        # self.analyzed_typedef_string = {}  # for debug

    def _get_cache(self, k):
        res = self.cache_.get_type_cache(k)
        logging.debug("{}get type {} from cache".format("" if res != None else "cannot ", k))
        if res == None:
            self.cache_.add_type_cache(k, {})
            return False, None
        elif res == {}:
            res["cached"] = "InProcess"
            res["cache_k"] = k
            return True, res
        else:
            t = {"cached": "Done", "cache_k": k}
            return True, t
    
    # @log_durations(logging.debug)
    def parse_global_namespace(self, file, cflags): 
        if self.global_ns_ == None:
            generator_path, generator_name = utils.find_xml_generator('castxml')
            config = parser.xml_generator_configuration_t(
                xml_generator_path = generator_path,
                xml_generator = generator_name,
                compiler = 'clang++',
                ccflags=cflags
            )
            logging.info("Start parsing... {}".format(time.ctime(time.time())))
            decls = parser.parse([file], config, parser.COMPILATION_MODE.ALL_AT_ONCE)
            self.global_ns_ = declarations.get_global_namespace(decls)
    
    # @log_durations(logging.debug)
    def start_analyze(self, file, cflags, cls, output=None, sort_keys=False):
        '''
            @cls: str, name of the class/struct which needed be analyzed
            @output: default `None`, the json result will be save as files whose path is `output`
            @sort_keys: default `False`, sort the json when dump to file when this flag is `True`
        '''
        self.file_ = file
        self.cflags_ = cflags
        self.parse_global_namespace(self.file_, self.cflags_)
        self.res = self.analyze_string(cls)
        logging.debug("result for {}: \n{}".format(cls, json.dumps(self.res, indent=4)))
        # logging.debug("analyzed_typedef_string: {}".format(json.dumps(self.analyzed_typedef_string, indent=4, sort_keys=True)))
        logging.debug("find_class_cost: {}ms\nnot_find_class_cost: {}msn\nfind_typedef_time: {}ms\nfind_enum_cost: {}ms".format(
            int(self.find_class_cost*1000),
            int(self.not_find_class_cost*1000),
            int(self.find_typedef_cost*1000),
            int(self.find_enum_cost*1000))) 
        if output:
            with open(output, "w") as f:
                json.dump(self.res, f, indent=4, sort_keys=sort_keys)
            with open(output[:-5]+"_dependence.json", "w") as f:
                json.dump(self.cache_.type_detail_cache_, f, indent=4, sort_keys=sort_keys)
    
    def pre_process_type_string(self, type_str):    
        """
            pre-process: remove const, deal with prefix '::'
        """
        logging.debug("analyze: {}".format(type_str))
        _type = type_str.strip()
        if _type.startswith("const"): _type = _type[5:].strip()
        if _type.endswith("const"): _type = _type[:-5].strip()
        if _type.endswith("const *"): _type = _type[:-7].strip() + " *"
        if _type.startswith("::"): _type = _type[2:].strip()
        logging.debug("analyze after process: {}".format(_type))
        return _type
    
    def is_string_fundamental(self, type_str):
        if type_str.startswith("signed"): type_str = type_str[6:].strip()
        if type_str.startswith("unsigned"): type_str = type_str[8:].strip()
        return type_str in self.FUNDAMENTAL_LIST
    
    def is_string_enum(self, type_str, black_list=["std::", "*", "tsl::", "<"]):
        for t in black_list:
            if t in type_str:
                return None
        _type = type_str.split("::")[-1]
        try:
            stime = time.time()
            self.find_enum_cost += time.time() - stime
            t = self.global_ns_.enum(_type)
            return True
        except:
            self.find_enum_cost += time.time() - stime
            return False
   
    def analyze_string(self, type_str):
        if type_str == None or type_str == "":
            return None
        _type = self.pre_process_type_string(type_str)
        res = {
            "type": _type,
            "decl_type": type_str
        }
        # get from cache
        ret, t = self._get_cache(type_str)
        if ret:
            res.update(t)
            return res
        
        if self.is_string_fundamental(_type):
            res["is_fundamental"] = True
        elif self.is_string_enum(_type):
            res["is_enum"] = True
        else:        
            res.update(self.analyze_string_typedef(_type))
            _type = res["typedef_type"] if res.get("is_typedef", None) else res["type"]
            if self.is_string_fundamental(_type):
                res["is_fundamental"] = True
            elif self.is_string_enum(_type):
                res["is_enum"] = True
            elif _type.strip()[-1] == "*":
                t = self.analyze_string_pointer(_type)
                res.update({} if t == None else t)
            else:
                t = self.analyze_string_container(_type)
                if t != None:
                    res.update(t)
                else:
                    t = self.analyze_string_class(_type)
                    res.update(t)
        self.cache_.add_type_cache(type_str, res)
        return res
    
    def analyze_string_pointer(self, type_str):
        res = {}
        res["is_pointer"] = True
        res["depointer_type"] = type_str[0 : -1].strip()
        t = self.analyze_string(res["depointer_type"])
        if t != None:
            res["depointer"] = t
        return res

    def analyze_string_class(self, cls_name):
        res = {}
        cls = self.find_class(cls_name)
        if cls != None:
            res = {
                "variables": [],
                "is_class": True
            }
            try:
                vars = cls.variables()
            except:
                logging.debug("class have no member var {}".format(cls_name))
            else:
                for var in vars:
                    r = self.analyze_var(var, str(cls.name))
                    if r != None:
                        res["variables"].append(r)
        return res
               
    def analyze_string_container(self, type_str):
        if type_str == None or type_str == "":
            return None
        res = {}
        # check container
        ret = self.is_container(type_str)
        if not ret:
            return None
        res["is_class"] = True
        res["is_container"] = True
        res["container_k_type"], res["container_v_type"] = self.parse_type_from_container(type_str)
        t = self.analyze_string(res.get("container_k_type", None))
        if t != None:
            res["container_k"] = t
        t = self.analyze_string(res.get("container_v_type", None))
        if t != None:
            res["container_v"] = t
        return res

    def analyze_string_typedef(self, type_str, black_list=["std::", "*", "tsl::"]):
        # self.analyzed_typedef_string.update({type_str:{}})
        for t in black_list:
            if t in type_str:
                return {}
        type = self.find_typedef(type_str)
        res = {}
        if type != None:
            res["is_typedef"] = True
            res["typedef_decl_type"] = str(type.decl_type)
            res["typedef_type"] = self.pre_process_type_string(str(type.decl_type))
            logging.debug("{} typedef {}".format(type_str, str(type.decl_type)))
        return res
    
    def analyze_var(self, var, parent_name):
        '''
        @param variable_t obj
        @return dict
        '''
        if self.filter_var(var, parent_name):
            return None
        ret, t = self._get_cache(str(var.decl_type))
        if ret:
            t.update({"name": str(var.name), "decl_type": str(var.decl_type)})
            return t
        res = self.analyze_var_common(var)
        
        if declarations.type_traits.is_pointer(var.decl_type):
            t = self.analyze_string_typedef(res["type"])
            res.update(t)
            res["is_pointer"] = True
            res["depointer_type"] = str(declarations.type_traits.remove_cv(declarations.type_traits.remove_pointer(var.decl_type)))
            r = self.analyze_string(res["depointer_type"])
            if r != None:
                res["depointer"] = r
        elif declarations.type_traits_classes.is_class(var.decl_type):
            t = self.analyze_string_typedef(res["type"])
            res.update(t)
            res["is_class"] = True
            _type = res["typedef_type"] if res.get("is_typedef", None) else res["type"]
            t = self.analyze_string_container(_type)
            if t != None:
                res.update(t)
            else:
                t = self.analyze_string_class(_type)
                res.update(t)
        elif declarations.type_traits.is_fundamental(var.decl_type):
            res ["is_fundamental"] = True
        elif declarations.type_traits_classes.is_enum(var.decl_type):
            res["is_enum"] = True
        else:
            res["is_unknown"] = True
        if res != None:
            self.cache_.add_type_cache(str(var.decl_type), res)
        return res
    
    def filter_var(self, var, parent_name):
        if self.only_public_var_ and str(var.access_type) != "public":
            return True
        if str(var.parent.name) != parent_name:
            return True
        return False
    
    def analyze_var_common(self, var):
        res={}
        # common
        res["decl_type"] = str(var.decl_type)
        res["name"] = str(var.name)
        # check const
        _type = declarations.type_traits.remove_reference(var.decl_type)
        _type = declarations.type_traits.remove_cv(_type)
        _type = self.pre_process_type_string(str(_type))
        res["type"] = _type
        return res
       
    def find_typedef(self, custom_type, depth=2):
        '''
        @depth: int, the number of the iterations to find the multi-typedef
        '''
        cnt = 0
        res = None
        while cnt < depth:
            if self.is_container(custom_type):
                break
            stime = time.time()
            _type = custom_type.split("::")[-1]
            try:
                res = self.global_ns_.typedefs(_type)[0]
                self.find_typedef_cost += time.time() - stime
                custom_type = str(res.decl_type)
            except RuntimeError as e:
                self.find_typedef_cost += time.time() - stime
                logging.debug("cannot get typedef for {}, {}".format(custom_type, str(e)))
                break
            finally: 
                cnt += 1
        return res

    def find_class(self, cls_name, black_list = ["std::", "tsl::", "mstd::"]):
        for t in black_list:
            if t in cls_name:
                return None
        try:
            stime = time.time()
            l = cls_name.split("::")
            if len(l) == 2:
                try:
                    cls = self.global_ns_.namespace(l[0].strip()).class_(l[1].strip())
                except:
                    try:
                        cls = self.global_ns_.class_(l[-1].strip())  # to find the struct whose decls in a class 
                    except:
                        raise
            else:
                try:
                    cls = self.global_ns_.class_(l[-1].strip())
                except:
                    try:
                        cls = self.global_ns_.class_(cls_name)
                    except:
                        raise
            self.find_class_cost += time.time() - stime
            if True in [a in cls.location.file_name for a in self.filepath_black_list_]:
                logging.debug("cls {} in filepath_black_list_, location: {}".format(cls_name, str(cls.location.file_name)))
                return None
        except Exception:
            self.not_find_class_cost += time.time() - stime
            logging.debug("cannot found class whose name is {}, {}".format(cls_name, traceback.format_exc()))
            return None
        return cls
        
    def is_container(self, decl_type):
        if "<" not in decl_type: 
            return False
        t = decl_type[0 : decl_type.find("<")]
        return t in self.VALUE_CONTAINERS or t in self.KV_CONTAINERS
        
    def parse_type_from_container(self, decl_type):
        if decl_type[0 : decl_type.find("<")] in self.VALUE_CONTAINERS:
            return None, self.split_template_definition(decl_type[decl_type.find("<")+1 : decl_type.rfind(">")], 1)[0]
        if decl_type[0 : decl_type.find("<")] in self.KV_CONTAINERS:
            tmp = self.split_template_definition(decl_type[decl_type.find("<")+1 : decl_type.rfind(">")], 2)
            return tmp[0], tmp[1]
    
    def split_template_definition(self, def_str, num):
        '''
            Example:
                input:  `'long, Ads_MKPL_Order *, std::less<long>, ads::allocator<std::pair<const long, Ads_MKPL_Order *> >'`
                output: `['long', 'Ads_MKPL_Order *', 'std::less<long>', 'ads::allocator<std::pair<const long, Ads_MKPL_Order *> >']`
        '''
        left  = ['[', '<', '(', '{']
        right = [']', '>', ')', '}']
        depth, start, pos = 0, 0, 0
        res_list = []
        for ch in def_str:
            if ch in left:
                depth += 1
            elif ch in right:
                depth -= 1
            elif ch == ',':
                if depth == 0:
                    res_list.append(def_str[start : pos].strip())
                    if len(res_list) >= num: 
                        return res_list
                    start = pos + 1
            pos += 1
        res_list.append(def_str[start :].strip())
        return res_list


def print_analysis_summary(analyzer, args, total_time):
    """
    Print analysis completion summary information

    Args:
        analyzer: Analyzer instance
        args: Command line arguments
        total_time: Total execution time (seconds)
    """
    print("\n" + "="*80)
    print("🎉 C++ Structure Analysis Completed!")
    print("="*80)

    # Basic information
    print(f"📁 {'Input File':<15}: {args.input}")
    print(f"🏗️  {'Analyzed Class':<15}: {args.cls}")
    print(f"📄 {'Output File':<15}: {args.output}")
    print(f"⏱️  {'Total Time':<15}: {total_time:.3f} seconds")
    print(f"📝 {'Log File':<15}: {args.log_file}")

    # Analysis configuration
    print(f"\n⚙️  Analysis Configuration:")
    print(f"   • {'Public Members Only':<25}: {'Yes' if args.only_public_var else 'No'}")
    print(f"   • {'Sort JSON Keys':<25}: {'Yes' if args.sort_keys else 'No'}")
    print(f"   • {'Compiler Flags':<25}: {args.cflags}")
    if args.file_path_black_list:
        print(f"   • {'Blacklisted Paths':<25}: {', '.join(args.file_path_black_list)}")

    # Performance statistics
    if hasattr(analyzer, 'find_class_cost') and hasattr(analyzer, 'find_typedef_cost'):
        print(f"\n📊 Performance Statistics:")
        print(f"   • {'Class Lookup Time':<25}: {int(analyzer.find_class_cost * 1000)} ms")
        print(f"   • {'Typedef Lookup Time':<25}: {int(analyzer.find_typedef_cost * 1000)} ms")
        print(f"   • {'Enum Lookup Time':<25}: {int(analyzer.find_enum_cost * 1000)} ms")
        print(f"   • {'Class Not Found Time':<25}: {int(analyzer.not_find_class_cost * 1000)} ms")

    # Cache statistics
    if hasattr(analyzer, 'cache_') and analyzer.cache_:
        cache_size = len(analyzer.cache_.type_detail_cache_)
        print(f"   • {'Type Cache Count':<25}: {cache_size} entries")
        if cache_size > 0:
            print(f"   • {'Cache Hit Rate':<25}: Improved analysis efficiency")

    # Analysis results statistics
    if hasattr(analyzer, 'res') and analyzer.res:
        print(f"\n📈 Analysis Results:")
        result = analyzer.res

        # Basic type information
        type_info = []
        if result.get('is_fundamental'):
            type_info.append("Fundamental Type")
        if result.get('is_enum'):
            type_info.append("Enum Type")
        if result.get('is_pointer'):
            type_info.append("Pointer Type")
        if result.get('is_class'):
            type_info.append("Class/Struct")
        if result.get('is_container'):
            type_info.append("Container Type")
        if result.get('is_typedef'):
            type_info.append("Type Alias")

        if type_info:
            print(f"   • Type Characteristics: {', '.join(type_info)}")

        # Member variables statistics
        if 'variables' in result and isinstance(result['variables'], list):
            variables = result['variables']
            var_count = len(variables)
            print(f"   • Total Member Variables: {var_count}")

            if var_count > 0:
                # Count different types of members
                fundamental_count = sum(1 for v in variables if v.get('is_fundamental'))
                pointer_count = sum(1 for v in variables if v.get('is_pointer'))
                container_count = sum(1 for v in variables if v.get('is_container'))
                class_count = sum(1 for v in variables if v.get('is_class') and not v.get('is_container'))
                enum_count = sum(1 for v in variables if v.get('is_enum'))

                # 使用左对齐格式化输出
                print(f"     - {'Fundamental Types':<20}: {fundamental_count}")
                print(f"     - {'Pointer Types':<20}: {pointer_count}")
                print(f"     - {'Container Types':<20}: {container_count}")
                print(f"     - {'Custom Classes':<20}: {class_count}")
                print(f"     - {'Enum Types':<20}: {enum_count}")

                # Count access permissions (if available)
                public_count = sum(1 for v in variables if v.get('is_public'))
                private_count = sum(1 for v in variables if v.get('is_private'))
                protected_count = sum(1 for v in variables if v.get('is_protected'))

                if public_count + private_count + protected_count > 0:
                    print(f"     - {'Public Members':<20}: {public_count}")
                    print(f"     - {'Private Members':<20}: {private_count}")
                    print(f"     - {'Protected Members':<20}: {protected_count}")

    # 结束信息
    print(f"\n✅ Analyze finished successfully!")
    print(f"📋 Please check the log: {args.log_file}")
    print(f"🔍 Please check for the dependence of struct [{args.cls}]: {args.output[:-5]+"_dependence.json"}")
    print(f"🔍 Please check for the analyze result for struct [{args.cls}]: {args.output}")
    print("="*80)


if __name__ == "__main__":
    args_parser = argparse.ArgumentParser(description='Analyze CPP struct/class, generate json detail.')
    args_parser.add_argument('--input', dest='input', required=False, default="../../My_Repository.h",
                        help='the path of the cpp header file')
    args_parser.add_argument('--class', dest='cls', required=False, default="MyClass",
                        help='the name of class/struct name which need to be analyzed')
    args_parser.add_argument('--output', dest='output', required=False, default="TODO.json",
                        help='the path of the json result')
    args_parser.add_argument('--cflags', dest='cflags', required=False, default='-std=c++11 -I. -I/usr/local/include -O0 -Wall')
    args_parser.add_argument('--sort_keys', dest='sort_keys', action='store_true', default=False,
                        help='sort the json keys when dump to file')
    args_parser.add_argument('--log_file', dest='log_file', required=False, default="./repo_analyzer.log",
                        help='the path of the log file')
    args_parser.add_argument('--only_public_var', dest='only_public_var', action='store_true', default=False,
                        help='only analyze the public variables of a class/struct')
    args_parser.add_argument('--file_path_black_list', dest='file_path_black_list', nargs='+', default=[],
                        help='the file path black list, the class/struct which is declared in the file under the paths will be ignored, such as xxx/xxx/3rd')
    args = args_parser.parse_args()

    if args.output == "TODO.json":
        args.output = args.cls + "_analyze.json"
    
    print("""
 ██████╗██████╗ ██████╗     ███████╗████████╗██████╗ ██╗   ██╗ ██████╗████████╗██╗   ██╗██████╗ ███████╗
██╔════╝██╔══██╗██╔══██╗    ██╔════╝╚══██╔══╝██╔══██╗██║   ██║██╔════╝╚══██╔══╝██║   ██║██╔══██╗██╔════╝
██║     ██████╔╝██████╔╝    ███████╗   ██║   ██████╔╝██║   ██║██║        ██║   ██║   ██║██████╔╝█████╗ 
██║     ██╔═══╝ ██╔═══╝     ╚════██║   ██║   ██╔══██╗██║   ██║██║        ██║   ██║   ██║██╔══██╗██╔══╝  
╚██████╗██║     ██║         ███████║   ██║   ██║  ██║╚██████╔╝╚██████╗   ██║   ╚██████╔╝██║  ██║███████╗
 ╚═════╝╚═╝     ╚═╝         ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝  ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝                                     
 █████╗ ███╗   ██╗ █████╗ ██╗  ██╗   ██╗███████╗███████╗██████╗                
██╔══██╗████╗  ██║██╔══██╗██║  ╚██╗ ██╔╝╚══███╔╝██╔════╝██╔══██╗               
███████║██╔██╗ ██║███████║██║   ╚████╔╝   ███╔╝ █████╗  ██████╔╝               
██╔══██║██║╚██╗██║██╔══██║██║    ╚██╔╝   ███╔╝  ██╔══╝  ██╔══██╗               
██║  ██║██║ ╚████║██║  ██║███████╗██║   ███████╗███████╗██║  ██║               
╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝   ╚══════╝╚══════╝╚═╝  ╚═╝               
""")
    print("Welcome! Start analyzing... {}\n".format(time.ctime(time.time())))               

    logging.basicConfig(level=logging.DEBUG, filename=args.log_file)
    clang_flag = args.cflags
    logging.debug("clang_flag = %s", args.cflags)

    start_time = time.time()
    analyzer = CppStructClassAnalyzer(only_public_var=args.only_public_var, file_path_black_list=args.file_path_black_list)
    analyzer.start_analyze(args.input, clang_flag, args.cls, output=args.output, sort_keys=args.sort_keys)
    total_time = time.time() - start_time

    # 输出总结信息
    print_analysis_summary(analyzer, args, total_time)

