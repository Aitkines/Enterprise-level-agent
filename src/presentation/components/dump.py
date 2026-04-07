import marshal

try:
    with open(r'c:\Users\Lenovo\Desktop\项目agent2.0\src\presentation\components\__pycache__\styles.cpython-311.pyc', 'rb') as f:
        f.read(16)
        code = marshal.load(f)

    for const in code.co_consts:
        if str(type(const)) == "<class 'code'>" and const.co_name == 'apply_global_styles':
            for i, c2 in enumerate(const.co_consts):
                if isinstance(c2, str) and len(c2) > 500:
                    out_path = fr'c:\Users\Lenovo\Desktop\项目agent2.0\src\presentation\components\css_dump_{i}.txt'
                    with open(out_path, 'w', encoding='utf-8') as out:
                        out.write(c2)
                    print(f"Dumped {len(c2)} bytes to {out_path}")
            break
except Exception as e:
    print(e)
