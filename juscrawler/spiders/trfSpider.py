import scrapy
from scrapy.http import FormRequest

import time
import datetime

class TrfspiderSpider(scrapy.Spider):
    name = 'trfSpider'
    start_urls = ['http://www5.trf5.jus.br/cp/']
    processo = None
    cpf_cnpj = None
    processos_conhecidos = None
    processos_desconhecidos = []
    pagination = 0
    search_desconhecidos = False
    urls = []
    
    def parse(self, response):
        
        if self.processos_conhecidos is not None and self.cpf_cnpj is not None:
            self.cpf_cnpj = self.cpf_cnpj.replace(".", "")
            self.cpf_cnpj = self.cpf_cnpj.replace("-", "")
            self.cpf_cnpj = self.cpf_cnpj.replace("/", "")
            self.search_desconhecidos = True
             
            data = {
                'filtroCpfRequest:': str(self.cpf_cnpj),
                'filtroCPF2': str(self.cpf_cnpj), 
                'navigation': 'Netscape',
                'tipo': 'xmlcpf',
                'filtro': '',
                'tipoproc': 'T',
                'filtroRPV_Precatorios':'', 
                'uf_rpv': 'PE',
                'numOriginario':'' ,
                'numRequisitorio':'', 
                'numProcessExec':'', 
                'uf_rpv_OAB': 'PE',
                'filtro_processo_OAB':'', 
                'filtro_CPFCNPJ':'' ,
                'campo_data_de': '',
                'campo_data_ate': '',
                'vinculados': 'true',
                'ordenacao': 'D',
                'ordenacao cpf': 'D',
                }
            
                    
            return [FormRequest(url='https://www4.trf5.jus.br/processo/cpf/porData/ativos/'+ self.cpf_cnpj + '/0',
                            callback=self.parse_desconhecidos, formdata=data)]
            
        
        elif self.cpf_cnpj is not None and self.processo is not None:
            self.cpf_cnpj = self.cpf_cnpj.replace(".", "")
            self.cpf_cnpj = self.cpf_cnpj.replace("-", "")
            self.cpf_cnpj = self.cpf_cnpj.replace("/", "")
            
            data = {
                'filtroCpfRequest:': str(self.cpf_cnpj),
                'filtroCPF2': str(self.cpf_cnpj), 
                'navigation': 'Netscape',
                'tipo': 'xmlcpf',
                'filtro': '',
                'tipoproc': 'T',
                'filtroRPV_Precatorios':'', 
                'uf_rpv': 'PE',
                'numOriginario':'' ,
                'numRequisitorio':'', 
                'numProcessExec':'', 
                'uf_rpv_OAB': 'PE',
                'filtro_processo_OAB':'', 
                'filtro_CPFCNPJ':'' ,
                'campo_data_de': '',
                'campo_data_ate': '',
                'vinculados': 'true',
                'ordenacao': 'D',
                'ordenacao cpf': 'D',
                }
                    
            return [FormRequest(url='https://www4.trf5.jus.br/processo/cpf/porData/ativos/'+ self.cpf_cnpj + '/0',
                            callback=self.parse_cpf_cnpj, formdata=data)]
            
        elif self.processo is not None:
            return [FormRequest.from_response(response,
                            formdata={'filtro': self.processo},
                            callback=self.parse_processo)]
            
            
    def parse_processo(self, response):
        numero_processo = response.xpath('/html/body/p[2]/text()').extract_first()
        numero_processo = numero_processo.replace(" ", "")
        numero_processo = numero_processo.split("PROCESSONº")[1]
        numero_legado = response.xpath('/html/body/p[3]/text()').extract_first()
        data_autuacao = response.xpath('/html/body/table[1]/tr[1]/td[2]/div/text()').extract_first()
        data_autuacao = self.format_date(data_autuacao)
        envolvidos_tables = response.xpath('/html/body/table[3]/tr')
        movimentacoes = response.xpath('/html/body/table')
        mv = {}
        envolvidos = {}
        
        itera = 2
        mov_itera = 0
        
        for tr in envolvidos_tables:
            left = tr.xpath('./td[1]/text()').extract_first()
            right = tr.xpath('./td[2]/b/text()').extract_first()
            
            if left not in envolvidos:
                envolvidos.update({'%s' % left : right})
            else:
                while((left + str(itera)) in envolvidos):
                    itera = itera + 1
                envolvidos.update({'%s' % left + str(itera) : right})
                itera = 2
        
        for table in movimentacoes:
            mov_itera = mov_itera + 1
            if(mov_itera < 6):
                continue
            else:
                data = table.xpath('./tr[1]/td/ul/li/a/text()').extract_first()
                desc = table.xpath('./tr[2]/td[2]/text()').extract_first()
                desc_detail = table.xpath('./tr[2]/td[3]/text()').extract_first()
                mv['m' + str(mov_itera-6)]= {'movimentacao': {
                        'data': self.format_date_time(data),
                        'descricao': desc,
                        'descricao_detalhada': desc_detail,
                    }
                } 

        if numero_processo is None:
            numero_processo = numero_legado
        elif numero_legado is None:
            numero_legado = numero_processo

        
        yield {
            'numero_processo': numero_processo,
            'numero_legado': numero_legado,
            'data_autuacao': data_autuacao,
            'envolvidos': envolvidos,
            'movimentacoes': mv,
        }


    def parse_cpf_cnpj(self, response):
        processos_table = response.xpath('//*[@id="wrapper"]/table/tr/td/table[3]/tbody/tr')
        url = response.url
        url = url[:-1]
        count = 0

        self.pagination = self.pagination + 1
        
        url = url + str(self.pagination)

        for processo in processos_table:
            count = count + 1
            if(count%2 != 0):
                nprocesso = processo.xpath('./td[2]/a/text()').extract_first()
                if(nprocesso == self.processo):
                    processo_url = 'https://www4.trf5.jus.br/' + processo.xpath('./td[2]/a/@href').extract_first()
                    yield scrapy.Request(
                        url=processo_url,
                        callback=self.parse_processo
                    )
                    return
                                
        yield scrapy.Request(
            url=url,
            callback=self.parse_cpf_cnpj
        )
    
    def parse_desconhecidos(self, response):
        processos_table = response.xpath('//*[@id="wrapper"]/table/tr/td/table[3]/tbody/tr')
        url = response.url
        url = url[:-1]
        count = 0
        q_total = response.xpath('/html/body/div[2]/div/div[2]/table/tr/td/table[2]/tr/td/table/tr/td[1]/span/text()').extract_first() #Total de Querys
        q_total = q_total.replace("Total: ", "")

        self.pagination = self.pagination + 1
        
        url = url + str(self.pagination)
        
        for processo in processos_table:
            count = count + 1
            if(count%2 != 0):
                nprocesso = processo.xpath('./td[2]/a/text()').extract_first()
                if nprocesso not in self.processos_conhecidos:
                        self.urls.append('https://www4.trf5.jus.br' + processo.xpath('./td[2]/a/@href').extract_first())
                if self.pagination < int(q_total)/10:
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_desconhecidos
                    )         
        for processos in self.urls:
            yield scrapy.Request(
                url=processos,
                callback=self.parse_processo
            )
                    
                    
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
    