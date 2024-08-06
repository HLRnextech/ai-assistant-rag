class CustomHttpError extends Error {
  constructor(message, status, data) {
    if (data && data.error && typeof data.error === "string") {
      super(data.error);
    } else {
      super(message);
    }
    this.status = status;
    this.data = data;
  }

  toString() {
    if (this.data && this.data.error && typeof this.data.error === "string") {
      return this.data.error;
    }
    return this.message;
  }
}

export { CustomHttpError };
