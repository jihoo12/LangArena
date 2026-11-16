/* Register unmodified algorithms from the adjacent LangArena checkout. */
#include "benchmark.h"

Benchmark *BinarytreesObj_create(void);
Benchmark *BinarytreesArena_create(void);
Benchmark *Matmul_create(void);
Benchmark *Sieve_create(void);
Benchmark *SortQuick_create(void);
Benchmark *SortMerge_create(void);
Benchmark *SortSelf_create(void);
Benchmark *BufferHashSHA256_create(void);
Benchmark *BufferHashCRC32_create(void);
Benchmark *Fannkuchredux_create(void);
Benchmark *Mandelbrot_create(void);
Benchmark *Spectralnorm_create(void);

int main(int argc, char **argv) {
  if (argc < 2) return 2;
  Helper_load_config(argv[1]);
#define REGISTER(name, factory) Benchmark_register(name, factory)
  REGISTER("Binarytrees::Obj", BinarytreesObj_create);
  REGISTER("Binarytrees::Arena", BinarytreesArena_create);
  REGISTER("Matmul::Single", Matmul_create);
  REGISTER("Etc::Sieve", Sieve_create);
  REGISTER("Sort::Quick", SortQuick_create);
  REGISTER("Sort::Merge", SortMerge_create);
  REGISTER("Sort::Self", SortSelf_create);
  REGISTER("Hash::SHA256", BufferHashSHA256_create);
  REGISTER("Hash::CRC32", BufferHashCRC32_create);
  REGISTER("CLBG::Fannkuchredux", Fannkuchredux_create);
  REGISTER("CLBG::Mandelbrot", Mandelbrot_create);
  REGISTER("CLBG::Spectralnorm", Spectralnorm_create);
  Benchmark_all(argc > 2 ? argv[2] : NULL);
  Helper_free_config();
  return 0;
}
