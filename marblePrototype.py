#!/usr/bin/python3

import itertools
import operator
import bisect
import sys

class ModelLeaf(object):
	def __init__(self, scale):
		self.symbols = {}
		self.exit = 0
		self.scale = scale

	def addSymbol(self, symbol, count):
		if symbol not in self.symbols:
			self.symbols[symbol] = 0
		self.symbols[symbol] += count

	def normalize(self, isRootLeaf):
		if isRootLeaf:
			self.exit = 0
		elif self.exit == 0:
			self.exit = 1

		currentScale = sum(self.symbols.values()) + self.exit
		desiredScale = self.scale

		if isRootLeaf:
			#print(self.symbols)
			zeroSymbols = 256 - len(self.symbols)
			desiredScale -= zeroSymbols
			#print("z {} d {}".format(zeroSymbols, desiredScale))

		if currentScale != 0:
			self.symbols = dict(filter(lambda s: s[1] != 0, itertools.starmap(lambda s, c: (s, c * desiredScale // currentScale), self.symbols.items())))
			self.exit = desiredScale - sum(self.symbols.values())
		else:
			self.exit = desiredScale

		if isRootLeaf:
			for i in range(256):
				symbol = bytes([i])
				if symbol not in self.symbols:
					self.symbols[symbol] = 1

		if self.totalCount() != self.scale:
			raise Exception("Can't normalize leaf!")

	def totalCount(self):
		return sum(self.symbols.values()) + self.exit

	def entriesCount(self):
		return len(self.symbols)

class Model(object):
	def __init__(self, order, leavesScale):
		self.order = order
		self.contexts = {}
		self.leavesScale = leavesScale

	def addSymbol(self, symbol, context, count = 1):
		if len(context) != self.order:
			raise Exception("Wrong context length!")
		if context not in self.contexts:
			self.contexts[context] = ModelLeaf(self.leavesScale)
		self.contexts[context].addSymbol(symbol, count)

	def totalCount(self):
		return sum(map(lambda leaf: leaf.totalCount(), self.contexts.values()))

	def entriesCount(self):
		return sum(map(lambda leaf: leaf.entriesCount(), self.contexts.values()))

	def leavesCount(self):
		return len(self.contexts)

def firstBit(val):
	return (val & 0x8000) != 0

def secondBit(val):
	return (val & 0x4000) != 0

class ArithmeticCoder(object):
	def __init__(self, consumer):
		self.low = 0
		self.high = 0xFFFF
		self.underflowBits = 0
		self.consumer = consumer

	def encode(self, pLow, pHigh, pScale):
		#print("{} {} {}".format(pLow, pHigh, pScale))
		if pLow >= pHigh:
			raise Exception("Invalid parameters! low: {}, high: {}".format(pLow, pHigh))
		currentRange = self.high - self.low + 1
		self.high = self.low + currentRange * pHigh // pScale - 1
		self.low = self.low + currentRange * pLow // pScale
		flag = True
		while flag:
			if firstBit(self.low) == firstBit(self.high):
				self.consumer.outputBit(firstBit(self.low))
				for n in range(self.underflowBits):
					self.consumer.outputBit(not firstBit(self.low))
				self.underflowBits = 0
				self.shift()
			elif secondBit(self.low) and not secondBit(self.high):
				self.underflowBits += 1
				self.low = self.low & 0x3FFF
				self.high = self.high | 0x4000
				self.shift()
			else:
				flag = False
				#raise Exception("Something went wrong! low: {}, high: {}, underflowBits: {}".format(self.low, self.high, self.underflowBits))
		#print("low: {}, high: {}, underflowBits: {}".format(self.low, self.high, self.underflowBits))

	def shift(self):
		self.low = (self.low << 1) & 0xFFFF
		self.high = ((self.high << 1) & 0xFFFF) | 0x0001


class OutputPrinter(object):
	def outputBit(self, bit):
		print("{}".format(int(bit)), end="", flush = True)

class OutputCollector(object):
	def __init__(self):
		self.data = []
		self.symbol = 0
		self.bitsCount = 0

	def outputBit(self, bit):
		self.symbol = (self.symbol << 1) | int(bit)
		self.bitsCount += 1
		if self.bitsCount == 8:
			self.data.append(self.symbol)
			self.bitsCount = 0

defaultScale = 256
highScale = 1024
models = [Model(0, highScale), Model(1, defaultScale), Model(2, defaultScale)]
maxOrder = len(models) - 1

def addToModel(symbol, context):
	if len(context) > maxOrder:
		raise Exception("Wrong context length!")
	models[len(context)].addSymbol(symbol, b"".join(context))

context = []
with open("1.txt", "rb") as f:
	byte = f.read(1)
	while byte:
		addToModel(byte, context)
		context.append(byte)
		if len(context) > maxOrder:
			context = context[1:]
		byte = f.read(1)

for model in models:
	print("Order: {}, total count: {}, entriesCount: {}, leavesCount: {}".format(model.order, model.totalCount(), model.entriesCount(), model.leavesCount()))
	sortedLeaves = list(sorted(model.contexts.items(), key=operator.itemgetter(0)))
	for context, leaf in sortedLeaves:
		sortedSymbols = list(sorted(leaf.symbols.items(), key=operator.itemgetter(0)))
		print("Context: {}".format(context))
		print("Entries: {}".format(sortedSymbols))

minLeafValue = 16
for model in models[-1:0:-1]:
	allLeaves = []
	for context, leaf in model.contexts.items():
		allLeaves.append((leaf.totalCount(), context, leaf))

	sortedLeaves = list(sorted(allLeaves, key=operator.itemgetter(0)))
	if sortedLeaves[0][0] >= minLeafValue:
		flag = False
	for count, context, leaf in filter(lambda l: l[0] < minLeafValue, sortedLeaves):
		print("Dropping {}".format(context))
		heirContext = context[1:]
		for symbol, count in leaf.symbols.items():
			models[len(heirContext)].addSymbol(symbol, heirContext, count)
		models[len(context)].contexts.pop(context)

for model in models:
	print("Order: {}, total count: {}, entriesCount: {}, leavesCount: {}".format(model.order, model.totalCount(), model.entriesCount(), model.leavesCount()))
	sortedLeaves = list(sorted(model.contexts.items(), key=operator.itemgetter(0)))
	for context, leaf in sortedLeaves:
		sortedSymbols = list(sorted(leaf.symbols.items(), key=operator.itemgetter(0)))
		print("Context: {}".format(context))
		print("Entries: {}".format(sortedSymbols))

for model in models:
	for context, leaf in model.contexts.items():
		leaf.normalize(len(context) == 0)

print("NORMALIZED")

for model in models:
	print("Order: {}, total count: {}, entriesCount: {}, leavesCount: {}".format(model.order, model.totalCount(), model.entriesCount(), model.leavesCount()))
	sortedLeaves = list(sorted(model.contexts.items(), key=operator.itemgetter(0)))
	for context, leaf in sortedLeaves:
		sortedSymbols = list(sorted(leaf.symbols.items(), key=operator.itemgetter(0)))
		print("Context: {}".format(context))
		print("Entries: {}".format(sortedSymbols))


def findModelLeafByContext(context):
	strcontext = b"".join(context)
	model = models[len(context)]
	if strcontext in model.contexts:
		return model.contexts[strcontext]
	return None

encodedData = OutputCollector()
coder = ArithmeticCoder(encodedData)
def encode(symbol, context):
	if len(context) > maxOrder:
		raise Exception("Wrong context length!")
	leaf = findModelLeafByContext(context)
	if not leaf:
		if len(context) == 0:
			raise Exception("Error: can't find appropriate leaf!")
		return encode(symbol, context[1:])
	if symbol not in leaf.symbols:
		coder.encode(leaf.scale - leaf.exit, leaf.scale, leaf.scale)
		if len(context) == 0:
			raise Exception("Error: can't find appropriate leaf!")
		return encode(symbol, context[1:])
	else:
		sortedSymbols = list(sorted(leaf.symbols.items(), key=operator.itemgetter(0)))
		index = bisect.bisect_left(list(map(operator.itemgetter(0), sortedSymbols)), symbol)
		low = 0
		for s, c in sortedSymbols[:index]:
			low += c
		#print(symbol)
		#print(sortedSymbols)
		#print(index)
		high = low + sortedSymbols[index][1]
		coder.encode(low, high, leaf.scale)

context = []
with open("1.txt", "rb") as f:
	byte = f.read(1)
	while byte:
		encode(byte, context)
		context.append(byte)
		if len(context) > maxOrder:
			context = context[1:]
		byte = f.read(1)

class ArithmeticDecoder(object):
	def __init__(self, models, consumer, source):
		self.low = 0
		self.high = 0xFFFF
		self.context = []
		self.consumer = consumer
		self.source = source

		self.code = 0
		for i in range(16):
			self.code = ((self.code << 1) & 0xFFFF) | self.source.inputBit()

	def addSymbol(self, symbol):
		self.context.append(symbol)
		if len(self.context) > maxOrder:
			self.context = self.context[1:]
		self.consumer.addSymbol(symbol)

	def decode(self):
		while self.source.hasData():
			self.doDecode(self.context)

	def doDecode(self, context):
		#print("context: {}".format(context))
		leaf = findModelLeafByContext(context)
		if not leaf:
			if len(context) == 0:
				raise Exception("Error: can't find appropriate leaf!")
			return self.doDecode(context[1:])

		currentRange = self.high - self.low + 1
		symbolProbability = ((self.code - self.low + 1) * leaf.scale - 1) // currentRange
		#print("code: {}, low: {}, high: {}, p: {}".format(self.code, self.low, self.high, symbolProbability))

		sortedSymbols = list(sorted(leaf.symbols.items(), key=operator.itemgetter(0)))
		low = 0
		index = 0
		for s, c in sortedSymbols:
			high = low + c
			if low <= symbolProbability and symbolProbability < high:
				self.addSymbol(s)
				self.symbolDecoded(low, high, leaf.scale)
				#print("symbol index: {}".format(index))
				return
			low = high
			index += 1
		self.symbolDecoded(leaf.scale - leaf.exit, leaf.scale, leaf.scale)
		self.doDecode(context[1:])

	def symbolDecoded(self, pLow, pHigh, pScale):
		#print("symbolDecoded(self, {}, {}, {})".format(pLow, pHigh, pScale))
		currentRange = self.high - self.low + 1
		self.high = self.low + currentRange * pHigh // pScale - 1
		self.low = self.low + currentRange * pLow // pScale
		while True:
			if firstBit(self.low) == firstBit(self.high):
				self.shift()
			elif secondBit(self.low) and not secondBit(self.high):
				self.low = self.low & 0x3FFF
				self.high = self.high | 0x4000
				self.code = self.code ^ 0x4000
				self.shift()
			else:
				return

	def shift(self):
		self.low = (self.low << 1) & 0xFFFF
		self.high = ((self.high << 1) & 0xFFFF) | 0x0001
		self.code = ((self.code << 1) & 0xFFFF) | self.source.inputBit()

class BitSource(object):
	def __init__(self, byteData):
		self.byteData = byteData
		self.index = 0
		self.bitsCount = 8

	def inputBit(self):
		if self.bitsCount == 0:
			self.index += 1
			self.bitsCount = 8
		result = (self.byteData[self.index] >> (self.bitsCount - 1)) & 0x1
		self.bitsCount -= 1
		return result

	def hasData(self):
		return self.index < len(self.byteData)

class SymbolPrinter(object):
	def addSymbol(self, symbol):
		print(symbol.decode("utf-8"), end="", flush=True)

for b in encodedData.data:
	for i in range(8):
		print((b >> (7 - i)) & 0x1, end="", flush=True)
print("")
print("Encoded size: {}".format(len(encodedData.data)))

decoder = ArithmeticDecoder(models, SymbolPrinter(), BitSource(encodedData.data))
decoder.decode()

