;;;; -*- mode: lisp -*-

;;; Future Chaining
;;
;; When an async call returns a future from *another* async call, the original
;; caller only needs to wait once.
;;
;; In the example below, `chain' knows that `chain1' returns a future, and so
;; uses `wait' to return the resolved wait. However, `chain1' calls `chain2',
;; which *also* returns a future, and `chain1' does not `wait' on its result.


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
  ;; Return value will be 4
  (wait (chain1 1)))
