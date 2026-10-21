import unittest,tempfile,base64
from pathlib import Path
from io import BytesIO
from PIL import Image
from pharmacy.core import Store
from pharmacy import branding,printing

class BrandingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.s=Store(self.root/'test.sqlite3'); self.s.setup('owner','strong-password'); self.s.login('owner','strong-password')
    def tearDown(self): self.s.close(); self.temp.cleanup()
    def logo(self,color='green',size=(240,80),format='PNG'):
        image=Image.new('RGB',size,color); out=BytesIO(); image.save(out,format=format); return out.getvalue()
    def test_replace_logo_and_remove_without_affecting_records(self):
        branding.save_profile(self.s,{'name':'First pharmacy','phone':'03000000000'},self.logo())
        first=branding.logo_bytes(self.s); self.assertIsNotNone(first)
        branding.save_profile(self.s,{'name':'Second pharmacy'},self.logo('blue'))
        self.assertNotEqual(first,branding.logo_bytes(self.s)); self.assertEqual(self.s.get_setting('name'),'Second pharmacy')
        self.assertEqual(self.s.scalar('SELECT count(*) FROM products'),0)
        branding.save_profile(self.s,{'name':'Second pharmacy'},b''); self.assertIsNone(branding.logo_bytes(self.s))
    def test_invalid_logo_does_not_partially_save_profile(self):
        branding.save_profile(self.s,{'name':'Original'},self.logo())
        for raw in (b'not an image',b'x'*(branding.MAX_FILE+1)):
            with self.assertRaises(ValueError): branding.save_profile(self.s,{'name':'Bad'},raw)
            self.assertEqual(self.s.get_setting('name'),'Original')
    def test_jpeg_normalized_resized_and_metadata_free(self):
        image=Image.open(BytesIO(branding.normalize_logo(self.logo(size=(2000,500),format='JPEG'))))
        self.assertEqual(image.format,'PNG'); self.assertEqual(image.size,(512,128)); self.assertEqual(image.mode,'RGBA')
    def test_logo_restored_with_legacy_schema_snapshot(self):
        branding.save_profile(self.s,{'name':'Backup pharmacy'},self.logo()); original=branding.logo_bytes(self.s)
        self.s.backup(self.root/'backup.sqlite3'); branding.save_profile(self.s,{'name':'Changed'},self.logo('blue'))
        self.s.restore(self.root/'backup.sqlite3'); self.s.login('owner','strong-password')
        self.assertEqual(branding.logo_bytes(self.s),original); self.assertEqual(self.s.get_setting('name'),'Backup pharmacy')
        self.assertEqual(self.s.scalar('SELECT version FROM meta'),1)
    def test_cashier_cannot_change_company_identity(self):
        self.s.add_user('cashier','cashier-password','Cashier'); self.s.login('cashier','cashier-password')
        with self.assertRaises(PermissionError): branding.save_profile(self.s,{'name':'Unauthorized'},self.logo())
    def test_pdf_logo_all_supported_sizes(self):
        logo=branding.normalize_logo(self.logo())
        for paper in ['A4','58mm','80mm']:
            path=self.root/(paper+'.pdf'); printing.pdf(path,'Customer receipt',['Pharmacy','Total PKR 365.00'],paper,logo)
            self.assertTrue(path.read_bytes().startswith(b'%PDF'))
    def test_profile_update_preserves_logo_when_not_replaced(self):
        branding.save_profile(self.s,{'name':'Original'},self.logo()); before=branding.logo_bytes(self.s)
        branding.save_profile(self.s,{'name':'Updated','email':'info@example.test'})
        self.assertEqual(branding.logo_bytes(self.s),before); self.assertEqual(self.s.get_setting('email'),'info@example.test')
    def test_legacy_database_without_logo_and_bad_encoding_safe(self):
        self.assertIsNone(branding.logo_bytes(self.s)); self.s.settings({'logo_png':'invalid base64'})
        self.assertIsNone(branding.logo_bytes(self.s))
if __name__=='__main__': unittest.main()
