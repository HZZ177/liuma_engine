# -*- coding: utf-8 -*-
import re
from assertpy import assertpy


class LMAssert:
    """断言"""

    def __init__(self, position, actual_result, expected_result):
        self.comparator = position
        self.actual_result = actual_result
        self.expected_result = expected_result

    def compare(self):
        try:
            if self.comparator in ["equal", "equals", "相等", "字符相等"]:  # 等于
                assertMsg = '实际值({})与预期值({}) 字符相等：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(str(self.actual_result)).is_equal_to(str(self.expected_result))
            elif self.comparator in ["equalsList", "数组相等"]:  # 列表相同，包括列表顺序也相同
                assertMsg = '实际值({})与预期值({}) 数组相等：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_type_of(list)
                assertpy.assert_that(self.actual_result).is_equal_to(LMAssert.str2list(self.expected_result))
            elif self.comparator in ["equalsDict", "对象相等"]:  # 字典相同
                assertMsg = '实际值({})与预期值({}) 对象相等：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_type_of(dict)
                assertpy.assert_that(self.actual_result).is_equal_to(LMAssert.str2dict(self.expected_result))
            elif self.comparator in ["equalsNumber", "数字相等", "数值相等"]:  # 数字等于
                assertMsg = '实际值({})与预期值({}) 数值相等：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_equal_to(LMAssert.str2num(self.expected_result))
            elif self.comparator in ["equalIgnoreCase", "相等(忽略大小写)"]:  # 忽略大小写等于
                assertMsg = '实际值({})与预期值({}) 相等(忽略大小写)：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(str(self.actual_result)).is_equal_to_ignoring_case(self.expected_result)
            elif self.comparator in ["notEqual", "does not equal", "不等于"]:  # 不等于
                assertMsg = '实际值({}) 不等于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(str(self.actual_result)).is_not_equal_to(str(self.expected_result))
            elif self.comparator in ["contains", "包含"]:  # 字符串包含该字符
                assertMsg = '实际值({}) 包含 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).contains(*LMAssert.str2tuple(self.expected_result))
            elif self.comparator in ["notContains", "does no contains", "不包含"]:  # 字符串不包含该字符
                assertMsg = '实际值({}) 不包含 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).does_not_contain(*LMAssert.str2tuple(self.expected_result))
            elif self.comparator in ["containsOnly", "仅包含"]:  # 字符串仅包含该字符
                assertMsg = '实际值({}) 仅包含 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).contains_only(*LMAssert.str2tuple(self.expected_result))
            elif self.comparator in ["isNone", "none/null"]:  # 为none或null
                assertMsg = '实际值({}) 为none或null：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2none(self.actual_result)).is_none()
            elif self.comparator in ["isNotNone", "notNone/notNull"]:  # 不为none或null
                assertMsg = '实际值({}) 不为none或null：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2none(self.actual_result)).is_not_none()
            elif self.comparator in ["notEmpty", "is not empty", "不为空"]:  # 不为空
                assertMsg = '实际值({}) 不为空：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_not_empty()
            elif self.comparator in ["empty", "is empty", "为空"]:  # 为空
                assertMsg = '实际值({}) 为空：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_empty()
            elif self.comparator in ["isTrue", "true"]:  # 是true
                assertMsg = '实际值({}) 是true：'.format(self.actual_result, self.expected_result)
                res = False if LMAssert.str2bool(self.actual_result) is None else LMAssert.str2bool(self.actual_result)
                assertpy.assert_that(res).is_true()
            elif self.comparator in ["isFalse", "false"]:  # 是false
                assertMsg = '实际值({}) 是false：'.format(self.actual_result, self.expected_result)
                res = True if LMAssert.str2bool(self.actual_result) is None else LMAssert.str2bool(self.actual_result)
                assertpy.assert_that(res).is_false()
            elif self.comparator in ["isStrType", "字符串"]:  # 是str的类型
                assertMsg = '实际值({}) 是字符串：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_type_of(str)
            elif self.comparator in ["isIntType", "整数"]:  # 是int的类型
                assertMsg = '实际值({}) 是整数：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_type_of(int)
            elif self.comparator in ["isFloatType", "浮点数"]:  # 是浮点的类型
                assertMsg = '实际值({}) 是浮点数：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_type_of(float)
            elif self.comparator in ["isInt", "is a number", "仅含数字"]:  # 字符串中仅含有数字
                assertMsg = '实际值({}) 仅含数字：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_digit()
            elif self.comparator in ["isLetter", "仅含字母"]:  # 字符串中仅含有字母
                assertMsg = '实际值({}) 仅含字母：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_alpha()
            elif self.comparator in ["isLower", "小写"]:  # 是小写的
                assertMsg = '实际值({}) 是小写的：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_lower()
            elif self.comparator in ["isUpper", "大写"]:  # 是大写的
                assertMsg = '实际值({}) 是大写的：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_upper()
            elif self.comparator in ["startWith", "开头是"]:  # 字符串以该字符开始
                assertMsg = '实际值({}) 开头是 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).starts_with(self.expected_result)
            elif self.comparator in ["endWith", "结尾是"]:  # 字符串以该字符结束
                assertMsg = '实际值({}) 结尾是 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).ends_with(self.expected_result)
            elif self.comparator in ["isIn", "has item", "包含对象", "被包含"]:  # 在这几个字符串中
                assertMsg = '实际值({}) 被包含在 预期值({}) 列表中：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_in(*LMAssert.str2tuple(self.expected_result))
            elif self.comparator in ["isNotIn", "不被包含"]:  # 不在这几个字符串中
                assertMsg = '实际值({}) 不被包含在 预期值({}) 列表中：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_not_in(*LMAssert.str2tuple(self.expected_result))
            elif self.comparator in ["isNotZero", "非0"]:  # 不是0
                assertMsg = '实际值({}) 不是0：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_not_zero()
            elif self.comparator in ["isZero", "为0"]:  # 是0
                assertMsg = '实际值({}) 是0：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_zero()
            elif self.comparator in ["isPositive", "正数"]:  # 是正数
                assertMsg = '实际值({}) 是正数：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_positive()
            elif self.comparator in ["isNegative", "负数"]:  # 是负数
                assertMsg = '实际值({}) 是负数：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(self.actual_result).is_negative()
            elif self.comparator in ["isGreaterThan", " 大于"]:  # 大于
                assertMsg = '实际值({}) 大于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_greater_than(LMAssert.str2num(self.expected_result))
            elif self.comparator in ["isGreaterThanOrEqualTo", "greater than or equal", ">=", " 大于等于"]:  # 大于等于
                assertMsg = '实际值({}) 大于等于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_greater_than_or_equal_to(LMAssert.str2num(self.expected_result))
            elif self.comparator in ["isLessThan", " 小于"]:  # 小于
                assertMsg = '实际值({}) 小于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_less_than(LMAssert.str2num(self.expected_result))
            elif self.comparator in ["isLessThanOrEqualTo", "less than or equal", "<=", " 小于等于"]:  # 小于等于
                assertMsg = '实际值({}) 小于等于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_less_than_or_equal_to(LMAssert.str2num(self.expected_result))
            elif self.comparator in ["isBetween", " 在...之间"]:  # 在...之间
                assertMsg = '实际值({}) 在 预期值({}) 之间：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_between(*LMAssert.str2tuple(self.expected_result))
            elif self.comparator in ["isCloseTo", " 接近于"]:  # 接近于
                assertMsg = '实际值({}) 接近于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.str2num(self.actual_result)).is_close_to(*LMAssert.str2tuple(self.expected_result))
            elif self.comparator in ["listLenEqual","列表长度相等"]:  # 列表长度相等
                assertMsg = '实际值({}) 列表长度相等 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.list_len(self.actual_result)).is_equal_to(LMAssert.str2num(self.expected_result))
            elif self.comparator in ["listLenGreaterThan","列表长度大于"]:  # 列表长度大于
                assertMsg = '实际值({}) 列表长度大于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.list_len(self.actual_result)).is_greater_than(LMAssert.str2num(self.expected_result))
            elif self.comparator in ["listLenLessThan","列表长度小于"]:  # 列表长度小于
                assertMsg = '实际值({}) 列表长度小于 预期值({})：'.format(self.actual_result, self.expected_result)
                assertpy.assert_that(LMAssert.list_len(self.actual_result)).is_less_than_or_equal_to(LMAssert.str2num(self.expected_result))
            else:
                raise AssertionTypeNotExist('没有{}该断言类型'.format(self.comparator))
            return True, assertMsg+", 条件为真"
        except AssertionError as e:
            return False, assertMsg+", 条件为假"

    @staticmethod
    def str2none(value):
        if str(value).lower() == "none" or str(value).lower() == "null":
            return None
        else:
            return value

    @staticmethod
    def str2bool(value):
        if str(value).lower() == "true":
            return True
        elif str(value).lower() == "false":
            return False
        else:
            return None

    @staticmethod
    def str2num(value):
        if type(value) == int or type(value) == float:
            return value
        if value is None or len(value) == 0:
            return None
        elif re.fullmatch(r'-?[0-9]*\.?[0-9]*', value) is not None:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        else:
            return value

    @staticmethod
    def str2tuple(value):
        if type(value) == tuple or type(value) == list:
            return tuple(value)
        elif value is None:
            return None,
        else:
            try:
                result = eval(value)
                if type(result) == list or type(result) == tuple:
                    return tuple(result)
                else:
                    return value,
            except:
                return value,

    @staticmethod
    def str2list(value):
        if value is None:
            return None
        elif type(value) == str and value.startswith('[') and value.endswith(']'):
            try:
                return eval(value)
            except:
                return value
        else:
            return value

    @staticmethod
    def str2dict(value):
        if type(value) == dict or type(value) == int or type(value) == float:
            return value
        if value is None or len(value) == 0:
            return None
        if value.startswith('{') and value.endswith('}'):
            try:
                return eval(value)
            except:
                return value
        else:
            return value

    @staticmethod
    def list_len(value):
        value2list = LMAssert.str2list(value)
        if type(value2list) != list:
            raise AssertionTypeNotExist('传入实际值({}) 不是列表格式'.format(value))
        else:
            return len(value2list)


class AssertionTypeNotExist(Exception):
    """断言类型错误"""
