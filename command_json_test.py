#!/usr/bin/env python

import tensorflow as tf
slim = tf.contrib.slim
from PIL import Image, ImageOps
from inception_resnet_v2 import *
import numpy as np
import json
import configargparse
import os
from os.path import splitext
import csv

#################
# 2. batch process
# 3. graph freeze
# 4. git upload
#################

# Batch size
#NUM_BATCH = 4

# Allowed image extension
IMG_EXT = ['.jpg', '.jpeg', '.png']

# Total classes
NUM_CLASSES = 1001

# Command line
parser = configargparse.ArgParser()
parser.add('--image_dir', dest='image_dir', required=True)
parser.add('--save_csv', dest='csv_file', default='classification_results_json.csv')
parser.add('--checkpoint_file', dest='checkpoint_file', default='graph_data/inception_resnet_v2_2016_08_30.ckpt')
parser.add('--label_file', dest='label_file', default='translate/result_imagenet1001.json')

args = vars(parser.parse_args())
sample_images_dir = args['image_dir']
#sample_images = os.listdir(sample_images_dir)
csv_file = args['csv_file']
checkpoint_file = args['checkpoint_file']
label_file = args['label_file']

# Load and convert label
label = open(label_file, 'r')
label = json.load(label)

# CSV UTF-8 Byte-Order-Mark
bom = open(csv_file, 'wb')
bom.write(bytearray(b'\xEF\xBB\xBF'))
bom.close()

# CSV format
result_csv = open(csv_file, 'ab')
field_names = ['directory', 'is_image', 'probability', 'index', 'kr_label']
result_writer = csv.DictWriter(result_csv, fieldnames=field_names)
result_writer.writeheader()

# Image preprocessing
def img_preproc(img, central_fraction=0.875):
	one_side_fraction = (1 - central_fraction) / 2.0
	im = Image.open(img)
	im = ImageOps.fit(im, (299, 299), method=2 ,bleed=one_side_fraction, centering=(0.5, 0.5))#method > BILINEAR=2 , NEAREST=0 (default)
	im = np.array(im).astype(dtype='float32')
	im = im.reshape(-1,299,299,3)
	im = 2*(im / 255.0) - 1.0
	return im

# Get Top5 infomations
def get_top5(prob):
	prob_with_idx = zip(prob[0], range(NUM_CLASSES))
	prob_with_idx.sort()
	return prob_with_idx[NUM_CLASSES-5:]

def get_info(image):
	im = img_preproc(image)
	predict_values, _ = sess.run([end_points['Predictions'], logits], feed_dict={im_tensor: im})
	return get_top5(predict_values)	

# Placeholder
im_tensor = tf.placeholder(tf.float32)
im_tensor = tf.reshape(im_tensor, [-1,299,299,3])

# Graph
sess = tf.Session()
arg_scope = inception_resnet_v2_arg_scope()
with slim.arg_scope(arg_scope):
	logits, end_points = inception_resnet_v2(im_tensor, is_training=False)
saver = tf.train.Saver()
saver.restore(sess, checkpoint_file)

# Main loop
print "--Main process start--"
is_image = False
for idx, (roots, _, files) in enumerate(os.walk(sample_images_dir)):
	print '-'*90
	print 'root name #',idx +1, '-', roots
	print '-'*90
	if files == []:
		print 'There are no files in this folder.'
		print '-'*45
	else:
		for jdx, file_name in enumerate(files):
			_, file_ext = splitext(file_name)
			if file_ext.lower() in IMG_EXT:
				is_image = True
				file_name = roots + '/' + file_name
				result_info = get_info(file_name)
				print "\tImage File name : #",jdx+1,"-",file_name
				for indx, j in enumerate(range(4, -1, -1)):
					print "\t\tTOP5 (predict value, index), (en_label), (kr_label) : #",indx+1, "-" , result_info[j], "(",label[str(result_info[j][1])].keys()[0],"), (",label[str(result_info[j][1])].values()[0],")"
					print '-'*45
					if indx == 0:
						result_writer.writerow({'directory':roots+'/'+file_name, 'is_image':is_image, 'probability':result_info[j][0], 'index':result_info[j][1], 'kr_label':label[str(result_info[j][1])].values()[0].encode('utf-8')})
					else:
						result_writer.writerow({'probability':result_info[j][0], 'index':result_info[j][1], 'kr_label':label[str(result_info[j][1])].values()[0].encode('utf-8')})
			else:
				is_image = False
				print '\t',file_name, 'is NOT an image file.'
				print '-'*45
				result_writer.writerow({'directory':roots+'/'+file_name, 'is_image':is_image})

print '='*90
print "--Process complete--"