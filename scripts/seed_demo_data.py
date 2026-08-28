"""生成演示文档（学生手册.md + 考勤.csv + 考勤.xlsx）并自动入库。

用法：python scripts/seed_demo_data.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows 控制台默认 GBK，强制 UTF-8 避免中文/emoji 输出报错
sys.stdout.reconfigure(encoding="utf-8")

import csv

from openpyxl import Workbook

import settings as config
from ingestion.pipeline import ingest_file

STUDENT_HANDBOOK_MD = """# 学生手册（示例）

## 第一章 总则
本校实行学分制管理，学生需在修业年限内修满培养方案规定的学分方可毕业。
本科生标准修业年限为四年，最长修业年限为六年。

## 第二章 学籍管理
1. 学生入学后三个月内完成学籍注册，逾期未注册者按自动退学处理。
2. 每学期开学后两周内办理注册手续，注册时需携带学生证。
3. 转专业申请时间为每学年第二学期末，须通过转入专业考核。
4. 休学期限累计不得超过两年；复学后应编入原专业相应年级。

## 第三章 考勤制度
1. 学生应按时上课，不得无故迟到、早退或缺勤。
2. 迟到超过15分钟按缺勤一节课处理；早退按迟到处理。
3. 一学期内无故缺勤累计达到10课时者，取消该课程期末考试资格。
4. 因病请假须持校医院证明，事假须提前向辅导员申请并获批。
5. 考勤记录由任课教师和班级考勤员共同登记，每月公示一次。

## 第四章 课程考核与成绩
1. 课程成绩由平时成绩（占30%）与期末成绩（占70%）构成。
2. 平时成绩包含出勤、作业与课堂表现，其中出勤占平时成绩的50%。
3. 课程考核不及格者可参加补考，补考仍不及格须重修。
4. 考试作弊者该课程成绩记为零分，并给予相应纪律处分。

## 第五章 奖学金评定
1. 一等奖学金：学年绩点不低于3.8，且无缺勤记录。
2. 二等奖学金：学年绩点不低于3.5，缺勤不超过2课时。
3. 三等奖学金：学年绩点不低于3.2，缺勤不超过4课时。
4. 奖学金每学年评定一次，评定结果公示五个工作日。

## 第六章 请假流程
1. 请假一天以内由辅导员批准；三天以内由院系批准；三天以上由教务处批准。
2. 请假需填写请假条，注明请假事由与起止时间。
3. 考勤数据每周汇总一次，作为期末考核与评优依据。

## 第七章 其他规定
1. 图书馆开放时间为每日 8:00—22:00，凭校园卡入馆。
2. 宿舍门禁时间为 23:00，晚归需登记。
3. 校园卡可在食堂、超市、图书馆等场所使用。
"""


def build_attendance_csv(path: Path) -> None:
    students = [("2023001", "张伟"), ("2023002", "李娜"), ("2023003", "王芳"), ("2023004", "刘洋")]
    dates = ["9月1日", "9月2日", "9月3日", "9月4日", "9月5日"]
    statuses = ["正常", "迟到", "正常", "缺勤", "早退"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["学号", "姓名", "日期", "节次", "状态"])
        for s_id, name in students:
            for day in dates:
                for period in (1, 2):
                    writer.writerow([s_id, name, day, period, random.choice(statuses)])


def build_attendance_xlsx(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "考勤记录"
    ws.append(["学号", "姓名", "日期", "节次", "状态"])
    students = [("2023005", "陈静"), ("2023006", "赵磊")]
    dates = ["9月1日", "9月2日", "9月3日"]
    for s_id, name in students:
        for day in dates:
            ws.append([s_id, name, day, 1, random.choice(["正常", "迟到", "正常"])])
    wb.save(path)


def main() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("生成演示文档…")

    md_path = config.DATA_DIR / "学生手册.md"
    md_path.write_text(STUDENT_HANDBOOK_MD, encoding="utf-8")

    csv_path = config.DATA_DIR / "考勤记录.csv"
    build_attendance_csv(csv_path)

    xlsx_path = config.DATA_DIR / "考勤记录.xlsx"
    build_attendance_xlsx(xlsx_path)

    for p in (md_path, csv_path, xlsx_path):
        try:
            result = ingest_file(p)
            print(f"  ✅ {p.name}: {result['chunk_count']} 个切片入库")
        except Exception as e:
            print(f"  ❌ {p.name}: {e}")

    print("\n完成。可启动服务：python main.py")


if __name__ == "__main__":
    main()
