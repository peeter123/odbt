
from odbt.main import odbtTest

def test_odbt(tmp):
    with odbtTest() as app:
        res = app.run()
        print(res)
        raise Exception

def test_command1(tmp):
    argv = ['command1']
    with odbtTest(argv=argv) as app:
        app.run()
