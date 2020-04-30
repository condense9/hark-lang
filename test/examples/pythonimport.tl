;;; -*- mode: lisp -*-

(importpy format :from pysrc.main)
(importpy cos :from math)


(def show-format (name)
  (format "Hello {}!" name))


(def show-trig (val)
  (cos val))
