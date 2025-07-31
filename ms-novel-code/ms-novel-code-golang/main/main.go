

package core

// import "fmt"

type Node struct {
	Val   int
	Left  *Node
	Right *Node
}

// rowWiseMax returns a map whose single key "output" holds the
// maximum node value found at each tree level, top-to-bottom.
func rowWiseMax(root *Node) map[string][]int {
	// Always return a non-nil slice, even for an empty tree.
	if root == nil {
		return map[string][]int{"output": []int{}}
	}

	var (
		res   []int   // result slice
		queue []*Node // simple FIFO queue
	)
	queue = append(queue, root)

	for len(queue) > 0 {
		levelSize := len(queue)
		maxVal := queue[0].Val // first node's value is current max

		// Process one level
		for i := 0; i < levelSize; i++ {
			node := queue[0]
			queue = queue[1:]

			if node.Val > maxVal {
				maxVal = node.Val
			}
			if node.Left != nil {
				queue = append(queue, node.Left)
			}
			if node.Right != nil {
				queue = append(queue, node.Right)
			}
		}
		res = append(res, maxVal)
	}

	return map[string][]int{"output": res}
}

// --- example usage ---
// func main() {
// 	root := &Node{Val: 10}
// 	root.Left = &Node{Val: 5}
// 	root.Right = &Node{Val: 4}
// 	root.Left.Left = &Node{Val: 8}
// 	root.Left.Right = &Node{Val: 9}
// 	root.Right.Right = &Node{Val: 15}

// 	fmt.Println(rowWiseMax(root))
// 	// Output: map[output:[10 5 15]]
// }