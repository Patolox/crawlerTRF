import scrapy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

import time
import datetime

class JusspiderSpider(scrapy.Spider):
    name = 'jusSpider'
    start_urls = ['http://www5.trf5.jus.br/cp/']
    processo = None
    cnpj_cpf = None
    processos_conhecidos = None
    processos_desconhecidos = []
    urls = []
    next_url = 0
    
    def __init__(self, **kwargs):
        chrome_options = Options()
        chrome_options.add_argument('--headless') #pondo o chrome em modo headless para não aparecer na tela, removam para ver o crawler funcionando em tempo real
        self.driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=ChromeDriverManager().install()) #utilizando o driver do chrome no selenium
        self.processo = kwargs.get('processo') # utilizando recurso da biblioteca scrapy para instanciar variaveis ( -a)
        self.cnpj_cpf = kwargs.get('cnpj_cpf')
        self.processos_conhecidos = kwargs.get('processos_conhecidos')
        
        
    def parse(self, response):
        self.driver.get(response.url)
        
        if self.cnpj_cpf is not None:
            checkCnpj_cpf = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*[@id="tipo_xmlcpf"]')))
            checkCnpj_cpf.click()
            nCnpj_cpf = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.NAME, 'filtroCPF2')))
            nCnpj_cpf.send_keys(self.cnpj_cpf)    
        
        elif self.processo is not None:
            nProcesso = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.NAME, 'filtro'))) # esperando o elemento carregar para então realizar operações
            nProcesso.send_keys(self.processo)

        submitConsulta = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*[@id="submitConsulta"]')))
        submitConsulta.click() # clicando no botão de consulta após colocar o numero do processo ou o cnpj_cpf no filtro de busca
        
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.driver.close() # fechando janela anterior
        self.driver.switch_to.window(self.driver.window_handles[0]) # mudando para a nova janela depois da anterior ter sido fechada
        
        if self.cnpj_cpf is not None and self.processo is not None: # scrap um processo de sua escolha
            cpf_cnpj_formatado = self.cnpj_cpf.replace(".", "")
            cpf_cnpj_formatado = cpf_cnpj_formatado.replace("-", "")
            cpf_cnpj_formatado = cpf_cnpj_formatado.replace("/", "")

            url = 'https://www4.trf5.jus.br/processo/cpf/porData/ativos/{}/0'.format(cpf_cnpj_formatado)
            yield scrapy.Request(
                url=url,
                callback=self.parse_cnpj_cpf,
            )
        
        elif self.cnpj_cpf is not None and self.processos_conhecidos is not None: # Busca processos desconhecidos
            cpf_cnpj_formatado = self.cnpj_cpf.replace(".", "")
            cpf_cnpj_formatado = cpf_cnpj_formatado.replace("-", "")
            cpf_cnpj_formatado = cpf_cnpj_formatado.replace("/", "")

            url = 'https://www4.trf5.jus.br/processo/cpf/porData/ativos/{}/0'.format(cpf_cnpj_formatado)
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_processo,
            )
            
        elif self.processo is not None: # scrap o processo direto
            self.html = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*')))
            yield scrapy.Request(
                url=response.url,
                callback=self.parse_processo,
            )

    def parse_search_processo(self, response):
        self.html = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*')))
        tbody = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_all_elements_located((By.XPATH,'//*[@id="wrapper"]/table/tbody/tr/td/table[3]/tbody/tr')))
        processo = None
        
        next_page = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*[@id="wrapper"]/table/tbody/tr/td/table[2]/tbody/tr/td/table/tbody/tr/td[2]/a[last()-1]')))
        
        for x in range(len(tbody)):
            if(x % 2 != 0):
                processo = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*[@id="wrapper"]/table/tbody/tr/td/table[3]/tbody/tr[{}]/td[2]/a'.format(x))))
                # processo = self.driver.find_element_by_xpath('//*[@id="wrapper"]/table/tbody/tr/td/table[3]/tbody/tr[{}]/td[2]/a'.format(x))

                if processo.text not in self.processos_conhecidos:
                    self.urls.append(processo.get_attribute('href'))
                    self.processos_desconhecidos.append(processo.text)
                    

        if next_page.text == '>':
            next_page.click()
            yield scrapy.Request(
                url= self.driver.current_url,
                callback=self.parse_search_processo,
            )
        elif len(self.processos_desconhecidos) > 0 :
            cpf_cnpj_formatado = self.cnpj_cpf.replace(".", "")
            cpf_cnpj_formatado = cpf_cnpj_formatado.replace("-", "")
            cpf_cnpj_formatado = cpf_cnpj_formatado.replace("/", "")
            self.driver.get(self.urls[0])
            for x in self.urls:
                self.html = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*')))
                yield scrapy.Request(
                    url=x,
                    callback=self.parse_processo,
                )
            
    def parse_cnpj_cpf(self, response):
        self.html = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*')))
        tbody = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_all_elements_located((By.XPATH,'//*[@id="wrapper"]/table/tbody/tr/td/table[3]/tbody/tr')))
        processo = None
        
        for x in range(len(tbody)):
            if(x % 2 != 0):
                processo = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*[@id="wrapper"]/table/tbody/tr/td/table[3]/tbody/tr[{}]/td[2]/a'.format(x))))
                # processo = self.driver.find_element_by_xpath('//*[@id="wrapper"]/table/tbody/tr/td/table[3]/tbody/tr[{}]/td[2]/a'.format(x))
             
                if processo.text == self.processo:
        
                    processo.click()

                    self.driver.switch_to.window(self.driver.window_handles[0])
                    self.driver.close() # fechando janela anterior
                    self.driver.switch_to.window(self.driver.window_handles[0]) # mudando para a nova janela depois da anterior ter sido fechada
        
                    self.html = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*')))
                            
                    yield scrapy.Request(
                        url=self.driver.current_url,
                        callback=self.parse_processo,
                    )
                    return
    
        next_page = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'//*[@id="wrapper"]/table/tbody/tr/td/table[2]/tbody/tr/td/table/tbody/tr/td[2]/a[last()-1]')))
        next_page.click()
    
        yield scrapy.Request(
            url= self.driver.current_url,
            callback=self.parse_cnpj_cpf,
        )
    def parse_processo(self, response): # obtem as informações do HTML na pagina de processo
        numero_processo = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'/html/body/p[2]')))
        numero_processo = numero_processo.text.replace(" ", "")
        numero_processo = numero_processo.split("PROCESSONº")[1]
        
        numero_legado = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'/html/body/p[3]')))
        numero_legado = numero_legado.text
        
        data_autuacao = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'/html/body/table[1]/tbody/tr[1]/td[2]/div')))
        data_autuacao = self.format_date(data_autuacao.text)
        
        relator = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,'/html/body/table[3]/tbody/tr[last()]/td[2]/b')))
        relator = relator.text
        
        movimentacoes = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_all_elements_located((By.XPATH,'/html/body/table')))

        mv = {}
        envolvidos = {}
        itera = 2
        
        for x in range(6, len(movimentacoes) + 1):
            dataPesquisa = '/html/body/table[{}]/tbody/tr[1]/td/ul/li/a'.format(x)
            descricaoPesquisa = '/html/body/table[{}]/tbody/tr[2]/td[2]'.format(x)
            descricaoDetalhada = '/html/body/table[{}]/tbody/tr[3]/td[2]'.format(x)
            
            data = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,dataPesquisa)))
            data = self.format_date_time(data.text)
            
            descricao = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,descricaoPesquisa)))
            descricao = descricao.text
            
            descricao2 = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_element_located((By.XPATH,descricaoDetalhada)))
            descricao2 = descricao2.text
            
            mv['m' + str(x-6)]= {'movimentacao': {
                           'data': data,
                           'descricao': descricao,
                           'descricao_detalhada': descricao2,
                       }
                    } 

        envolvidos_element = WebDriverWait(self.driver, 20).until(expected_conditions.presence_of_all_elements_located((By.XPATH,'/html/body/table[3]/tbody/tr')))
        
        for tr in envolvidos_element:
            left = tr.find_element_by_xpath('./td[1]').text
            right = tr.find_element_by_xpath('./td[2]/b').text
            
            if left == 'RELATOR':
                continue
            
            if left not in envolvidos:
                envolvidos.update({'%s' % left : right})
            else:
                while((str(itera) + left) in envolvidos):
                    itera = itera + 1
                envolvidos.update({str(itera) + '%s' % left : right})
                itera = 2
        
        if numero_processo is None:
            numero_processo = numero_legado
        elif numero_legado is None:
            numero_legado = numero_processo
            
        if self.urls is not None and self.next_url < len(self.urls):
            self.driver.get(self.urls[self.next_url])
            self.next_url = self.next_url + 1

        yield {
            'numero_processo': numero_processo,
            'numero_legado': numero_legado,
            'data_autuacao': data_autuacao,
            'relator': relator,
            'envolvidos': envolvidos,
            'movimentacoes': mv,
        }

        
    # x = datetime.datetime(2020, 5, 17, hora, minuto, segundo)
    def format_date(self, date): # lida apenas com as datas
        dformat = date.replace(" ", "")
        dformat = dformat.replace("AUTUADOEM", "")
        dformat = dformat.split('/')
        return datetime.datetime(int(dformat[2]), int(dformat[1]), int(dformat[0]))
    
    def format_date_time(self, date): # lida com data e hora
        dformat = date.split(' ')
        data = dformat[1].split('/')
        hora_minuto = dformat[2].split(':')
        return datetime.datetime(int(data[2]), int(data[1]), int(data[0]), int(hora_minuto[0]), int(hora_minuto[1]))
    
