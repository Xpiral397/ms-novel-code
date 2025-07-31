# Dockerfile
FROM golang:1.24

WORKDIR /app

# Install gotestsum
RUN go install gotest.tools/gotestsum@latest

# 1) Copy only go.mod and download deps (caches unless you change go.mod)
COPY go.mod ./
RUN go mod tidy

# 2) Copy your code & tests into the module root
COPY main/*.go ./
COPY test/*.go ./

# 3) Re-resolve deps now that both code & tests are here
RUN go mod tidy

# 4) Run all tests with gotestsum

CMD ["gotestsum", "--format", "short-verbose", "."]
