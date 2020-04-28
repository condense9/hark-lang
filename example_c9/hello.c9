;; -*- mode: lisp -*-
(importpy hi :from src.example :as say-hi)
(importpy format :from src.example)
(importpy sleep :from src.example)
(importpy random_sleep :from src.example)

(defun simple (do_sleep)
  (say-hi)
  (print (format "python formatting: {}, {}" 1 "foo"))
  (print (= 2 1))
  (print (list 1 2))
  (print (conc 1 (list 2)))
  (print (conc 1 nil))
  (print (conc 1 (conc 2 (conc 3 nil))))

  (let ((x "a binding")
        (y 2))
    (print x)
    (print y))

  (if do_sleep (sleep 0.5) nil)
  "something")


(defun go-async ()
  (let ((a (async simple nil))
        (b (async simple t)))
    (print "done main")
    (list (wait a) (wait b))))


(defun main ()
  (let ((x (async simple t))
        (y (+ 2 3)))
    (print (format "sleep result: {}" (wait x)))
    (format "sum: {}" y)))

(defun printer (x)
  (print (format "You gave me: {}" x))
  x)


;; Concurrent tests

(defun a (x)
  (print "a starting to sleep")
  (random_sleep 200 500)
  (print "a finished sleeping")
  (+ x 1))

(defun b (x)
  (print "b starting to sleep")
  (random_sleep 200 500)
  (print "b finished sleeping")
  (* (a x) 1000))

(defun c (x)
  (print "c starting to sleep")
  (random_sleep 200 500)
  (print "c finished sleeping")
  (+ x -1))

(defun d (x)
  (print "d starting to sleep")
  (random_sleep 200 500)
  (print "d finished sleeping")
  (* (c x) 10))

(defun e (p q)
  (+ $p (* (wait q) -1)))

(defun concurrent (x)
  ;; (1000 * (x + 1)) - (10 * (x - 1)) = 5960 if x is 5
  (e (async b x)
     @(d x)))


;;; Test Chain logic:

(defun chain3 (x)
  ;; -> 4
  (sleep 0.5)  ; Sleep a little to make sure the futures get chained
  (+ 1 x))

(defun chain2 (x)
  ;; -> future
  (async chain3 (+ 1 x)))

(defun chain1 (x)
  ;; -> future -> future
  (async chain2 (+ 1 x)))

(defun chain ()
  ;; only one wait is required to wait for N futures
  (wait (chain1 1)))
