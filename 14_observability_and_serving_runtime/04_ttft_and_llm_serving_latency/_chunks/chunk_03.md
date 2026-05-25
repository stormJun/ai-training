ing

![fragm](./paged_attention_assets/15_fragm.svg)

In addition to the huge size of the caches, early LLM serving systems
also handled memory allocations inefficiently. This is because during
inference, output sequence lengths are unknown in advance. You can
imagine this yourself when prompting: some prompts are short, others are
long, and each can generate either a long detailed output or a very
short one. Now scale this across thousands of users. To deal with this
uncertainty, serving platforms used to statically allocate a chunk of
memory for each request based on its maximum possible sequence length,
regardless of the actual input or the eventual output length. They did
this using preallocation schemes that ensured there was enough memory to
hold a request’s *potential* maximum KV cache size, even if that space
was never fully used.

The diagram above illustrates how the two types of fragmentation appear.
I adapted the figure from the paper but used the same example prompts we
have been following in this blog so it feels consistent. Here I call it
request A, with a very simple request B alongside it. In practice you
can imagine many more requests batched together of course. As you can
see, there are two primary sources of memory waste:

1.  Reserved slots for future tokens: If a generation finishes early and
    uses fewer tokens than the maximum, the remaining allocated memory
    stays unused but unavailable for others. This is **internal
    fragmentation**.
2.  **External fragmentation** from the memory allocator, such as the
    buddy allocator. This one is a little more subtle, so let us walk
    through an example.

<div style="text-align:center">

<img src="./paged_attention_assets/16_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

We start with 128 free bytes. Request A arrives needing 32 bytes. The
allocator keeps halving the bar until it can hand out 0 to 31, leaving
32 to 63 and 64 to 127 free. Request B needs 16 bytes. We carve it from
the right side, split 64 to 127, then 64 to 95, and allocate 64 to 79.
Now 80 to 95 and 96 to 127 are free, with the allocated block sitting in
between. Request C is tiny, just 7 bytes. The allocator splits 32 to 63
down to an 8 byte piece and allocates 32 to 39, leaving 1 byte inside
that piece unused (**internal fragmentation**). At this point the GPU
still has plenty of free memory in total: 40 to 47, 48 to 63, 80 to 95,
and 96 to 127, which add up to 72 bytes. But then a new long request
arrives that needs 64 bytes in one piece. Even though there is enough
free memory overall, there is no single contiguous block of that size,
since 64 to 79 is already occupied and the left side has been split into
smaller fragments. The allocation fails. This is **external
fragmentation**, and it is exactly the kind of waste that naive per
request KV slabs caused, since earlier LLM serving systems stored each
request’s KV cache in contiguous memory with preallocated slabs.

Both forms of fragmentation are pure waste. Even though reserved memory
is eventually consumed, holding it aside for the entire lifetime of a
request especially when the reserved space is large blocks other
requests from using it in the meantime.

## Paging as the Analogy

**Paged Attention** borrows directly from **virtual memory** and
**paging** in operating systems like Unix and Windows. Instead of
treating memory as one large block, the OS divides it into page frames
and only keeps the active parts in fast memory.

LLM serving faces the same problem with the KV cache. By paging it, we
can allocate memory more efficiently, avoid waste, and support much
longer contexts. Before getting into paged KV caching and paged
attention, I think it helps to quickly revisit this operating systems
analogy to later draw the mapping between both concepts.

### Operating Systems analogy

Memory pressure has always been a concern in computing. Software
generally tends to grow faster than memory, so systems needed a way to
run programs that were larger than available memory, and also to run
multiple programs at once whose combined size exceeded what could fit.
The proposed solution was therefore *virtual memory*.

The idea is that each program gets its own **virtual address space**,
divided into fixed-sized **pages**, while physical memory is divided
into **page frames** of the same size. A small mapping structure records
which virtual page currently lives in which physical frame, and because
of this indirection, a program can behave as if all of its memory were
present, while in reality the system only keeps the working set in fast
memory.

For example, imagine the instruction MOV REG,1000, where 1000 is some
computed virtual address. On a system without virtual memory, that
address is sent directly to the memory bus and the word at that position
is accessed. With virtual memory, things go first through the **memory
management unit (MMU)**, which consults the page
table<span class="sidenote-ref"></span> <span class="sidenote"
style="counter-increment:none"> Mathematically speaking, the page table
is a function, with the virtual page number as argument and the physical
frame number as the output. </span>If the page is present, the access
succeeds immediately and is sent to the bus. If it is absent (which is
indicated through a hardware present/absent bit), the MMU triggers a
**page fault**, and the operating system fetches the missing page from
slower storage, places it into a free frame, updates the mapping, and
retries the instruction.

<div style="text-align:center">

<img src="./paged_attention_assets/17_transformers.svg"
style="width:80.0%" alt="Transformers" />

</div>

I try to make this structure clear with my drawing, but I guess a simple
example on it could make things clearer. Suppose we have this 64 KB
virtual address space but only 32 KB of physical memory. The virtual
space is divided into 16 pages of 4 KB each, and physical memory into 8
frames of 4 KB. If the table says that virtual page 0 is currently in
frame 2, then any access in that page is redirected there. If virtual
page 2 is mapped to frame 6, it goes to frame 6. But if virtual page 8
is marked absent, the MMU raises a fault, the OS fetches that page from
disk into a frame, updates the mapping, and execution
continues.<span class="sidenote-ref"></span><span class="sidenote"
style="counter-increment:none"> Because translations happen constantly,
systems need ways to make them fast. That’s where techniques like
translation lookaside buffers (TLBs) and multi-level page tables come
in. We won’t go deep into them here, but it’s useful to know they exist.
</span>

That’s all we need from the operating systems side. Virtual memory gives
the *illusion* of a large, continuous address space by mapping it onto a
smaller pool of fast memory and moving pages in and out as needed. Now
lets carry these concepts to paged KV caching and later paged attention.

### Paged KV Caching

Paged KV caching applies the same paging idea to the KV cache. Inside
vLLM, the **KV cache manager** is the heart of paged KV caching.
Essentially, the KV cache manager owns memory for keys and values and
the **scheduler** decides which requests advance each step. The key
difference then is that the cache manager does not hand each request one
giant contiguous buffer to store all of its keys and values. Instead, it
breaks the cache into fixed size **KV blocks** measured in tokens per
block akin to pages as we saw before, keeps a **global free block
pool**, which you can think of as a doubly linked list, and gives each
request a small **block table** that maps its logical blocks to physical
blocks (a.k.a page frames) in GPU memory. When a request grows, new
blocks are taken from the pool and appended to its table. When a request
finishes, its blocks go back to the pool and can be reused immediately
by any other request.

<div style="text-align:center">

<img src="./paged_attention_assets/18_vllm.svg" style="width:80.0%"
alt="vllm" />

</div>

The top part is the **engine** view which I have adapted from [Aleksa's
post](https://www.aleksagordic.com/blog/vllm). Requests come in, the
processor prepares them turning raw input into a suitable request format
i.e tokenisation, the scheduler picks which ones to run, and the KV
cache manager sits in the middle coordinating memory. The middle part is
the indexing structure on the CPU side we talked about, which we can
think of as a doubly linked list of available block identifiers managed
by the cache manager and the bottom view is the real KV data on the GPU,
stored as many equal sized blocks. The block table is the bridge which
are also maintained by the KV cache manager. Block table is the main
table used to map logical KV blocks to their computed KV cache blocks
even when the physical blocks are actually scattered.

At initialisation the engine measures how much VRAM is available for
cache, chooses a token block size $`B`$, and computes how many blocks
fit. For a standard transformer layer the bytes per block are:

``` math
bytes = 2\times B\times num\_ kv\_ heads\times head\_ size\times bytes
```

The factor two accounts for keys and values. With GQA or MQA,
num_kv_heads becomes smaller, so each block becomes lighter and more
blocks fit in the same memory.

During execution vLLM allocates just in time rather than predicting the
full future length. In each engine step the scheduler decides which
requests advance, then asks the KV cache manager to reserve blocks only
for the tokens processed in this step. For prefill the number of new
tokens is known upfront, so the manager allocates
$`\lceil N\div B\rceil`$ blocks for a prompt of $`N`$ tokens. For decode
the step usually adds a single token<span class="sidenote-ref"></span>
<span class="sidenote" style="counter-increment:none">  
In V1 the engine scheduler can mix both prefill and decoding stages in
the same step. In V0, which I am following here for simplification and
to keep consistency with Aleksa's work, only one of the two can happen
at any time.  
</span>. The manager checks the remaining free slots in the last logical
block and allocates a new block only when that block would overflow in
this step. Similarly, when a request completes, its blocks are returned
to the pool. Because every block has the same size, any returned block
can satisfy any future block request.

<div style="text-align:center">

<img src="./paged_attention_assets/19_transformers.webp"
style="width:60.0%" alt="Transformers" />

</div>

![pagedkv](./paged_attention_assets/20_pagedkv.gif)

These two diagrams show a simple prompt and how that would look like
from the logical and physical memory view and how they are mapped in the
block table. Suppose the prompt has 7 tokens and $`B = 4`$. We need
$`\lceil 7\div 4\rceil = 2`$ KV blocks. The manager pops two identifiers
from the free pool and writes them into the request’s block table. Each
entry tracks the physical block id, a small reference count, and often a
block hash. The reference count enables memory sharing. When two
requests share an identical prefix, they both point to the same physical
blocks and the counts increase. No copying is needed, we will see this
next. During decode, new tokens are written into the next free slots.
When the last block fills, one more block is appended and the table
grows by one entry.

A crucial note to make clear: blocks are read shared, write unique. A
physical KV block is write owned by a single request. You never let an
unrelated request place a token into the spare slot of someone else’s
block. If two requests share an identical prefix they can both read the
same blocks, and the reference counts increase. The moment one of them
needs to append, the cache manager allocates a fresh block for that
request, which is effectively copy on write at block granularity. As you
realise, that means there can be some small unused tails within the
final block of a request, which is