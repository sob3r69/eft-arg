import { useEffect, useRef } from 'react';

import classes from './ErrorModal.module.css';

interface ErrorModalProps {
  isOpen:  boolean;
  onClose: () => void;
}

export function ErrorModal({ isOpen, onClose }: ErrorModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;

    if (!dialog || !isOpen) {
      dialog?.close();
      return;
    }

    dialog.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
      dialog.close();
    };
  }, [isOpen]);

  return (
    <dialog
      ref={dialogRef}
      className={classes.dialog}
      aria-labelledby="error-modal-title"
      aria-describedby="error-modal-message"
      onClose={onClose}
    >
      <h2 id="error-modal-title" className={classes.title}>Критическая ошибка</h2>
      <p id="error-modal-message" className={classes.message}>1000 - Backend error</p>
      <form method="dialog" className={classes.actions}>
        <button type="submit" className={classes.confirmButton} aria-label="OK">
          <img src="/images/error-modal/ok-button.png" alt="" width="196" height="52" />
        </button>
      </form>
    </dialog>
  );
}
