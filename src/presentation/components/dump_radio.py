import marshal

try:
    with open(r'c:\Users\Lenovo\Desktop\项目agent2.0\src\presentation\components\__pycache__\styles.cpython-311.pyc', 'rb') as f:
        f.read(16)
        code = marshal.load(f)

    for const in code.co_consts:
        if str(type(const)) == "<class 'code'>" and const.co_name == 'apply_global_styles':
            for i, c2 in enumerate(const.co_consts):
                if isinstance(c2, str):
                    print(f'String {i} size {len(c2)}')
                    if 'stHorizontalRadio' in c2:
                        with open(r'c:\Users\Lenovo\Desktop\项目agent2.0\src\presentation\components\radio_css.txt', 'w', encoding='utf-8') as out:
                            out.write(c2)
                        print('Found stHorizontalRadio!')
except Exception as e:
    print(e)
