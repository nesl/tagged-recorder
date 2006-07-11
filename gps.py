import socket, re, string, select, time

class GPS:
	"""Manage a connection to a GPS device (as represented by gpsd)"""
	
	def __init__(self, host = '127.0.0.1', port = 2947, debug = 0):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((host, port))
		self.debug = debug
		self.data = {}
		self.quest = re.compile("\?")
		self.time_re = re.compile("^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})?(\.(\d+))Z$")
		self.update()
  
	def __del__(self):
		# Close socket gracefully
		self.sock.close()
  
	def update(self):
		"""Fetch the latest status from gpsd"""
		self.sock.send("PDAVSM")
		result = self.sock.recv(2048)
		result = result[:-1].rstrip()
		if self.debug == 1:
			print >> sys.stderr, ">GPSD: PDAVSM" 
			print >> sys.stderr, "GPSD>: %s" % result
		chunks = string.split(result, ',')
		if chunks[0] != "GPSD":
			return
		for chunk in chunks[1:]:
			noquest = self.quest.sub("-1", chunk[2:])
			self.data[chunk[0]] = string.split(noquest, ' ')
  
	def position(self):
		"""Return latest latitude/longitude position array"""
		if self.data['P'][0] == "-1":
		  self.data['P'] = ["361", "361"]
		return (float(self.data['P'][0]), float(self.data['P'][1]))
  
	def altitude(self):
		"""Return latest altitude (meters)"""
		return float(self.data['A'][0])
  
	def velocity(self):
		"""Return latest velocity (knots)"""
		return float(self.data['V'][0])
  
	def status(self, text = 0):
		"""Return latest GPS status"""
		status = int(self.data['S'][0])
		if text:
			return ('NONE', 'GPS', 'dGPS')[status]
		else:
			return status
  
	def mode(self, text = 0):
		"""Return latest mode"""
		mode = int(self.data['M'][0])
		if text:
			return ('NO-FIX', '2D-FIX', '3D-FIX')[mode - 1]
		else:
			return mode
  
	def time(self):
		"""Return GPS time of last sample (UTC, secs-since-epoch)"""
		try:
		  #jtime = string.join(self.data['D'], ' ')
		  #tm = time.strptime(jtime, '%m/%d/%Y %H:%M:%S')
		  ma = self.time_re.match(self.data['D'][0])
		  if ma:
		    tm = time.strptime("%s%s%s%s%s%s" % (ma.group(1), ma.group(2), \
		                                         ma.group(3), ma.group(4), \
		                                         ma.group(5), ma.group(6)), \
		                                         "%Y%m%d%H%M%S")
		  else:
		    return 0
		except ValueError:
			return 0
		return int(time.mktime(tm) + 0.5)
  
