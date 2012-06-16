from package.unittest import *

class TestImport(TestCase):
    def test_import(self):
        import ooni

        self.assertTrue(True, 'ooni module imported cleanly')

if __name__ == '__main__':
    main()
