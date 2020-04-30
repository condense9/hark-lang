;;;; -*- mode: lisp -*-

;;; Concurrency
;;
;; Functions `conc-b' and `conc-d' are called asynchronously from `concurrent'
;; (using two different syntaxes, just for funs). Functions `ser-a' and `ser-c'
;; are called normally.
;;
;; So the evaluation/data-flow graph looks like:
;;
;;                        .---[ conc-b ]---[ ser-a ]--.
;;                       /                             \
;; X --[ concurrent ]---<                               >---[ final ]--->
;;                       \                             /
;;                        ·---[ conc-d ]---[ ser-c ]--·
;;



(defun ser-a (x)
  (print "a starting to sleep")
  ;; (random_sleep 200 500)
  (sleep 1)
  (print "a finished sleeping")
  (+ x 1))

(defun conc-b (x)
  (print "b starting to sleep")
  (print "b finished sleeping")
  (* (ser-a x) 1000))

(defun ser-c (x)
  (print "c starting to sleep")
  (sleep 1)
  (print "c finished sleeping")
  (+ x -1))

(defun conc-d (x)
  (print "d starting to sleep")
  (print "d finished sleeping")
  (* (ser-c x) 10))

(defun final (p q)
  (+ $p (* (wait q) -1)))

(defun concurrent (x)
  ;; (1000 * (x + 1)) - (10 * (x - 1)) = 5960 if x is 5
  (final (async conc-b x)
         @(conc-d x)))
