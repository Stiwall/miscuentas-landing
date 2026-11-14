import unittest
from test_seo_20261028 import SeoPublico
class SeoNoviembre(SeoPublico):
 def test_producto(self):self.assertTrue(self.html('/').select('a[href="/app-contable"]'))
 def test_urls(self):self.assertFalse([a['href'] for a in self.html('/').select('a[href]') if a['href'].endswith('.html')])
 def test_plazos(self):self.assertNotIn('obliga a todos los negocios a emitir e-CF a partir de noviembre 2026',self.html('/blog/miscuentas-vs-alegra').get_text())
 def test_mes(self):self.assertNotIn('no lo dejes para octubre',self.html('/blog/prorroga-ecf-15-noviembre-2026').get_text())
