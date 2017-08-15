pos_tags = [""]
pos_descriptions = ["placeholder for index zero"]
with open("pos.txt","rb") as f:
	for line in f:
		num,tag,description=line.split(b"\t")
		pos_tags.append(tag.strip().decode("utf8"))
		pos_descriptions.append(description.strip().decode("utf8"))
with open("pos.py","wb") as pospy:
	pospy.write(b"pos_tags = "+bytes(repr(pos_tags),encoding="utf8")+b"\n")
	pospy.write(b"pos_descriptions = "+bytes(repr(pos_descriptions),encoding="utf8")+b"\n")
