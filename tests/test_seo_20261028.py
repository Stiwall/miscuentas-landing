import json, threading, unittest, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from bs4 import BeautifulSoup

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path != '/' and not path.endswith('/') and not Path('.'+path).suffix:
            self.path=path+'.html'
        super().do_GET()

class SeoPublico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls): cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def html(self,path):
        with urllib.request.urlopen(self.base+path,timeout=5) as r:
            self.assertEqual(r.status,200); return BeautifulSoup(r.read(),'html.parser')
    def test_enlace_contextual_a_comparacion_excel(self):
        page=self.html('/blog/software-contable-republica-dominicana')
        links=[a.get('href','') for a in page.find_all('a')]
        self.assertTrue(any(x.rstrip('/').endswith('miscuentas-vs-excel') for x in links))
        self.assertEqual(len(self.html('/blog/miscuentas-vs-excel').select('h1')),1)
    def test_comparacion_evita_ahorro_y_testimonio_no_acreditados(self):
        page=self.html('/blog/miscuentas-vs-excel'); text=page.get_text(' ',strip=True)
        self.assertNotIn('Ahorro mensual estimado',text)
        self.assertNotIn('Dueño de ferretería, Santiago de los Caballeros',text)
        self.assertIn('plan Free',text)
        self.assertIn('US$19/mes',text)
    def test_comparacion_no_promete_ahorro_o_disponibilidad_absoluta(self):
        text=self.html('/blog/miscuentas-vs-excel').get_text(' ',strip=True)
        for phrase in ['el tiempo ya superó el costo de cualquier software','La única ventaja real de Excel','Lo que Excel nunca podrá hacer por ti en RD','siempre disponible']:
            self.assertNotIn(phrase,text)
    def test_titulo_ncf_incluye_contexto_dominicano(self):
        page=self.html('/blog/que-es-el-ncf-republica-dominicana')
        self.assertIn('República Dominicana',page.title.get_text())
        self.assertIn('NCF',page.title.get_text())
    def test_calendario_identifica_vencimientos_en_titulo(self):
        page=self.html('/blog/calendario-fiscal-dgii-2026')
        self.assertIn('vencimientos',page.title.get_text().lower())
        self.assertIn('2026',page.title.get_text())
    def test_sitemap_y_datos_articulo_indican_actualizacion(self):
        page=self.html('/blog/miscuentas-vs-excel')
        structured=[json.loads(s.string or s.get_text()) for s in page.select('script[type="application/ld+json"]')]
        art=next(x for x in structured if x.get('@type')=='Article')
        with urllib.request.urlopen(self.base+'/sitemap.xml',timeout=5) as r: root=ET.fromstring(r.read())
        ns={'x':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        entry=next(x for x in root.findall('x:url',ns) if x.find('x:loc',ns).text.endswith('/blog/miscuentas-vs-excel'))
        self.assertEqual(entry.find('x:lastmod',ns).text,art['dateModified'])
        self.assertEqual(art['dateModified'],'2026-10-28')

if __name__=='__main__':unittest.main(verbosity=2)
