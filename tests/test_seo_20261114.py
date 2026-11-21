import unittest
import test_seo_20261028 as soporte
class ServidorSEO(unittest.TestCase):
 setUpClass = classmethod(soporte.SeoPublico.setUpClass.__func__)
 tearDownClass = classmethod(soporte.SeoPublico.tearDownClass.__func__)
 html = soporte.SeoPublico.html
class SeoNoviembre(ServidorSEO):
 def test_producto(self):self.assertTrue(self.html('/').select('a[href="/app-contable"]'))
 def test_urls(self):self.assertFalse([a['href'] for a in self.html('/').select('a[href]') if a['href'].endswith('.html')])
 def test_plazos(self):self.assertNotIn('obliga a todos los negocios a emitir e-CF a partir de noviembre 2026',self.html('/blog/miscuentas-vs-alegra').get_text())
 def test_mes(self):self.assertNotIn('no lo dejes para octubre',self.html('/blog/prorroga-ecf-15-noviembre-2026').get_text())

class ComparativaActual(ServidorSEO):
 def test_fuente_y_sin_equivalencia_falsa(self):
  p=self.html('/blog/miscuentas-vs-alegra');t=p.get_text(' ',strip=True)
  self.assertTrue(p.select('a[href="https://www.alegra.com/rdominicana/precios/"]'))
  self.assertIn('14 de noviembre de 2026',t)
  for x in ['90% de lo que necesitas','un 34%','USD$29 × 5','más usado en República Dominicana']:
   self.assertNotIn(x,t)
 def test_guias_conectan_producto(self):
  for slug,target in [('como-hacer-606-607-dgii','/app-contable'),('software-contable-republica-dominicana','/contadores')]:
   self.assertTrue(self.html('/blog/'+slug).select('a[href="'+target+'"]'))

class CanalesDePrecios(ServidorSEO):
 def test_los_precios_de_la_app_llevan_a_la_tabla_del_canal_correcto(self):
  app = self.html('/app-contable')
  self.assertTrue(app.select_one('a[href="/precios#planes-en-linea"]'))
  precios = self.html('/precios')
  online = precios.select_one('#planes-en-linea')
  self.assertIn('Básico US$19/mes', online.get_text(' ', strip=True))
  self.assertIn('Pro US$49/mes', online.get_text(' ', strip=True))
  self.assertEqual([p.get_text(strip=True) for p in precios.select('.pamount')],
                   ['RD$0', 'RD$299', 'RD$600', 'RD$1,200'])
  self.assertEqual(len(precios.select('#planes a[href^="https://wa.me/"]')), 3)
