import scrapy
from bs4 import BeautifulSoup

class FAQExtractor(scrapy.Spider):
	name = 'FAQExtractor'
	start_urls = [
		'INSERT HERE THE URL'
	]

	def parse(self, response):
		threeFirstContentColumns = 3
		for contentCategorie in response.css('.content-categories-lu-portal')[:threeFirstContentColumns]:
			categoriesUrls = contentCategorie.css('a::attr(href)').getall()
			for i, url in enumerate(categoriesUrls[:1]):
				goToCategory = response.urljoin(url)
				yield scrapy.Request(goToCategory, callback=self.parseTopics)

	def parseTopics(self, response):
		topicsUrls = response.css('.bordered a.info-page-search-lu-portal::attr(href)').getall()
		for topicUrl in topicsUrls[:5]:
			goToTopic = response.urljoin(topicUrl)
			yield scrapy.Request(url=goToTopic, callback=self.parseFAQ)

		nextPages = response.css('.page::attr(href)').getall() 
		for nextPage in nextPages:
			yield response.follow(nextPage, callback=self.parseTopics)

	def parseFAQ(self, response):
		index_name = ''.join(response.css('.header-articles-lu-portal h1::text').getall())
		index_name = self.removeHtmlOnText(index_name)

		self.paragraphs = response.css('.content-articles-lu-portal p')
		self.paragraphs = [p for p in self.paragraphs if p.attrib != {'align': 'center'}]
		while self.paragraphs:
			p = self.paragraphs[0]
			
			fontColor, fontSize = self.getFontColorAndFontSize(p)
			if isinstance(fontSize, str) and int(fontSize) < 4: # if is out of pattern
				self.paragraphs = self.paragraphs[1:]
				continue


			if fontColor in ['#6600cc', '9900ff']: 
				subtopic = self.getSubtopic(p)

				if "saiba mais" not in subtopic:
					nextParagraphs = self.paragraphs[1:]
					description = self.getDescriptionUpToNewSubtopic(nextParagraphs)

					if len(description.split()) <= 500:
						if subtopic:
							yield {
								'index_name': subtopic,
								'items': description,
							}
						else:
							raise Exception('Sem subtopic')
							
					else:
						self.paragraphs = self.paragraphs[1:]
				else:
					self.paragraphs = self.paragraphs[1:]
			else:
				self.paragraphs = self.paragraphs[1:]



	def removeHtmlOnText(self, text):
		return BeautifulSoup(text, "html.parser").text

	def getFontColorAndFontSize(self, paragraph):
		fontColor = paragraph.css('strong font::attr(color)').get()
		if not fontColor:
			if paragraph.css('font strong'):
				fontColor = paragraph.css('font::attr(color)').get()	
			else:
				fontColor = paragraph.css('font::attr(color)').get()	
				if not fontColor:
					fontSize = paragraph.css('font::attr(size)').get()
					return fontColor, fontSize
				return fontColor, None
		return fontColor, None

	def getSubtopic(self, paragraph):
		subtopic = paragraph.css('font strong::text').getall()
		if not subtopic:
			subtopic = paragraph.css('font::text').getall()
			if not subtopic:
				subtopic = paragraph.css('::text').getall()
		
		subtopic = ''.join(subtopic).lower()
		return BeautifulSoup(subtopic, "html.parser").text

	def getDescriptionUpToNewSubtopic(self, paragraphsAfterSubtopic):
		if paragraphsAfterSubtopic:
			self.paragraphsAfterSubtopic = paragraphsAfterSubtopic
			self.nextSubtopicIndex = self.getNextSubtopicIndex()
			self.paragraphsBeforeSubtopic = self.paragraphsAfterSubtopic[:self.nextSubtopicIndex]
			self.paragraphs = self.paragraphsAfterSubtopic[self.nextSubtopicIndex:]
			
			description = self.getDescription()
			if description == '':
				raise Exception('Erro que não tá pegando texto.')
			
			return description

	def getNextSubtopicIndex(self):
		setcolors = [p.css('font::attr(color)').get() for p in self.paragraphsAfterSubtopic]
		if setcolors[0] == '#6600cc' and len(setcolors) > 1:
			setcolors = setcolors[1:]

		areParagraphsSubtopic = [color == '#6600cc' for color in setcolors]# for colors in setcolors]
		nextSubtopicIndex = areParagraphsSubtopic.index(True) if True in areParagraphsSubtopic else len(setcolors)
		return nextSubtopicIndex

	def getDescription(self):
		description = [''.join(p.css('::text').getall()) for p in self.paragraphsBeforeSubtopic]
		description = self.getDescriptionWithoutSaibaMais(description)
		description = '\n'.join(description)
		description = self.cleanText(description)
		return description

	def getDescriptionWithoutSaibaMais(self, descriptions):
		saibaMaisStopWords = ['aiba mais', 'aber mais']
		saibaMaisInText = lambda description: any([True for text in saibaMaisStopWords if text in description])
		indexesSaibaMais = [i for i, desc in enumerate(descriptions) if saibaMaisInText(desc)]
		if indexesSaibaMais:
			return descriptions[:indexesSaibaMais[0]]
		return descriptions

	@staticmethod
	def cleanText(text):
		text = BeautifulSoup(text, "html.parser").text
		text = text.replace('\xa0', '')
		text = text.lower()
		text = text.replace('\r', '')
		text = text.replace('  ', '\n')
		return text