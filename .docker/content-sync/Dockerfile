# Build stage
FROM --platform=$BUILDPLATFORM golang:1.23.0-alpine AS builder

WORKDIR /app

# Install git for go modules
RUN apk add --no-cache git

# Repo klonen
RUN git clone https://github.com/castai/openwebui-content-sync.git ./

# Download dependencies
RUN go mod download

# Build the application for the target platform
ARG TARGETOS
ARG TARGETARCH
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -a -installsuffix cgo -o main .

# Final stage
FROM --platform=$TARGETPLATFORM alpine:latest

# Install ca-certificates for HTTPS requests
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/main .

# Create data directory
RUN mkdir -p /data

# Expose port (if needed for health checks)
EXPOSE 8080

# Run the application
CMD ["./main"]